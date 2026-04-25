"""Execution API — core flow endpoints.

GET  /execute           → claim task, assemble prompt, return to AI
POST /execute/{id}/deliver  → AI submits results, system validates
POST /execute/{id}/heartbeat → AI keeps lease alive
POST /execute/{id}/fail     → AI marks execution failed
POST /execute/{id}/challenge → trigger challenge command generation
"""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select, and_, not_, text
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    Task,
    Execution,
    PromptSection,
    PromptElement,
    OutputContract,
    Change,
    Decision,
    Finding,
    AuditLog,
    task_dependencies,
    ExecutionAttempt,
)
from app.services.prompt_parser import assemble_prompt
from app.services.contract_validator import validate_delivery, CheckResult
from app.config import settings
from app.validation.rule_adapter import EvaluationContext
from app.validation.rules import contract_validator_rule
from app.validation.shadow_comparator import compare_and_log
from app.validation.state_transition import commit_status_transition

router = APIRouter(prefix="/api/v1", tags=["execution"])


# --- Helpers ---

def _get_contract(db: Session, task_type: str, ceremony_level: str) -> dict:
    """Lookup output contract with fallback chain: exact → wildcard type → wildcard ceremony → default."""
    for tt, cl in [(task_type, ceremony_level), ("*", ceremony_level), (task_type, "*"), ("*", "*")]:
        contract = db.query(OutputContract).filter(
            OutputContract.task_type == tt,
            OutputContract.ceremony_level == cl,
            OutputContract.active == True,
        ).order_by(OutputContract.version.desc()).first()
        if contract:
            return contract.definition
    return {"required": {"reasoning": {"min_length": 50}}, "optional": {}, "anti_patterns": {}}


def _determine_ceremony(task_type: str, ac_count: int) -> str:
    if task_type in ("chore", "investigation"):
        return "LIGHT"
    if task_type == "bug" and ac_count <= 3:
        return "LIGHT"
    if task_type == "feature" and ac_count <= 3:
        return "STANDARD"
    return "FULL"


def _next_external_id(db: Session, project_id: int, prefix: str) -> str:
    """Generate next external ID (D-001, C-001, F-001, etc.)."""
    from sqlalchemy import func
    model_map = {"D": Decision, "C": Change, "F": Finding}
    model = model_map.get(prefix)
    if not model:
        return f"{prefix}-001"
    max_id = db.query(func.max(model.external_id)).filter(model.project_id == project_id).scalar()
    if not max_id:
        return f"{prefix}-001"
    num = int(max_id.split("-")[1]) + 1
    return f"{prefix}-{num:03d}"


def _audit(db: Session, project_id: int | None, entity_type: str, entity_id: int, action: str, actor: str, **kwargs):
    db.add(AuditLog(
        project_id=project_id, entity_type=entity_type, entity_id=entity_id,
        action=action, actor=actor, **kwargs,
    ))


# --- GET /execute ---

@router.get("/execute")
def get_execute(
    project: str = Query(...),
    agent: str = Query("default"),
    lean: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Claim next available task, assemble prompt, return to AI with contract."""

    # Find project
    from app.models import Project
    proj = db.query(Project).filter(Project.slug == project).first()
    if not proj:
        raise HTTPException(404, f"Project '{project}' not found")

    # Find next TODO task with met dependencies using FOR UPDATE SKIP LOCKED
    done_ids_q = select(Task.id).where(Task.project_id == proj.id, Task.status.in_(("DONE", "SKIPPED")))
    done_ids = {r[0] for r in db.execute(done_ids_q).all()}

    # Find candidate with row-level lock
    candidate = None
    todo_tasks = db.query(Task).filter(
        Task.project_id == proj.id,
        Task.status == "TODO",
    ).with_for_update(skip_locked=True).all()

    for t in todo_tasks:
        dep_ids = {d.id for d in t.dependencies}
        if dep_ids and not dep_ids.issubset(done_ids):
            continue
        candidate = t
        break

    if not candidate:
        db.rollback()
        return Response(status_code=204)

    # Claim task — fire K1 detection at execute time per ADR-028 §K1.
    # Hook never breaks the claim path (failures caught inside post_commit
    # wrapper in commit_status_transition).
    now = dt.datetime.now(dt.timezone.utc)
    def _k1_hook_execute():
        from app.services.kill_criteria import detect_k1_for_task
        detect_k1_for_task(db, candidate.id)
    commit_status_transition(
        candidate, entity_type="task", target_state="IN_PROGRESS",
        post_commit=_k1_hook_execute,
    )
    candidate.agent = agent
    candidate.started_at = now

    # Determine ceremony
    ac_count = len(candidate.acceptance_criteria)
    ceremony = _determine_ceremony(candidate.type, ac_count)
    candidate.ceremony_level = ceremony

    # Get contract
    contract_def = _get_contract(db, candidate.type, ceremony)

    # Create execution
    lease_expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.lease_duration_minutes)

    execution = Execution(
        task_id=candidate.id,
        agent=agent,
        status="PROMPT_ASSEMBLED",
        contract=contract_def,
        lease_expires_at=lease_expires,
    )
    db.add(execution)
    db.flush()  # get execution.id

    # Assemble prompt
    result = assemble_prompt(db, candidate, execution, operation_type="implement", lean=lean)

    execution.prompt_text = result.prompt_text
    execution.prompt_hash = result.prompt_hash
    execution.prompt_meta = result.prompt_meta

    # Save sections and elements
    for sec in result.sections:
        sec.execution_id = execution.id
        db.add(sec)
    db.flush()

    # Link elements to sections
    section_map = {s.position: s.id for s in result.sections}
    for elem in result.elements:
        elem.execution_id = execution.id
        if elem.section_id == 0 and elem.position in section_map:
            elem.section_id = section_map[elem.position]
        db.add(elem)

    _audit(db, proj.id, "execution", execution.id, "created", f"agent:{agent}",
           new_value={"task_id": candidate.external_id, "prompt_kb": result.prompt_meta["total_kb"]})

    db.commit()

    # Build response
    ac_data = [
        {
            "position": ac.position,
            "text": ac.text,
            "scenario_type": ac.scenario_type,
            "verification": ac.verification,
            "test_path": ac.test_path,
            "command": ac.command,
        }
        for ac in candidate.acceptance_criteria
    ]

    excluded = [
        {"source": e.source_external_id or e.source_table, "reason": e.exclusion_reason}
        for e in result.elements if not e.included
    ]

    return {
        "execution_id": execution.id,
        "task": {
            "id": candidate.external_id,
            "name": candidate.name,
            "type": candidate.type,
            "status": candidate.status,
            "instruction": candidate.instruction,
            "description": candidate.description,
            "acceptance_criteria": ac_data,
            "produces": candidate.produces,
            "alignment": candidate.alignment,
            "exclusions": candidate.exclusions,
        },
        "prompt": {
            "full_text": result.prompt_text,
            "hash": result.prompt_hash,
            "meta": result.prompt_meta,
            "excluded": excluded,
        },
        "contract": {
            "ceremony_level": ceremony,
            **contract_def,
        },
        "lease_expires_at": lease_expires.isoformat(),
    }


# --- POST /execute/{id}/deliver ---

@router.post("/execute/{execution_id}/deliver")
def post_deliver(
    execution_id: int,
    delivery: dict,
    db: Session = Depends(get_db),
):
    """AI submits delivery. System validates against contract."""

    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(404, "Execution not found")
    if execution.status not in ("PROMPT_ASSEMBLED", "IN_PROGRESS", "REJECTED"):
        raise HTTPException(409, f"Execution status {execution.status} — cannot deliver")

    task = db.query(Task).filter(Task.id == execution.task_id).first()
    contract = execution.contract or {}

    # Check max attempts
    if execution.attempt_number > settings.max_delivery_attempts:
        commit_status_transition(execution, entity_type="execution", target_state="FAILED")
        commit_status_transition(task, entity_type="task", target_state="FAILED")
        task.fail_reason = f"Max delivery attempts ({settings.max_delivery_attempts}) exceeded"
        db.commit()
        raise HTTPException(422, f"Max attempts exceeded ({settings.max_delivery_attempts})")

    # Load previous attempts for resubmit detection
    prev_attempts = db.query(ExecutionAttempt).filter(
        ExecutionAttempt.execution_id == execution.id
    ).order_by(ExecutionAttempt.attempt_number.desc()).all()
    prev_attempt_dict = None
    if prev_attempts:
        pa = prev_attempts[0]
        prev_attempt_dict = {
            "attempt_number": pa.attempt_number,
            "verdict": pa.verdict,
            "delivery": pa.delivery_payload,
            "validation": pa.validation_result,
            "reasoning_hash": pa.reasoning_hash,
            "evidence_hash": pa.evidence_hash,
        }

    # Compute hashes for duplicate detection
    import hashlib
    reasoning_str = (delivery.get("reasoning") or "").strip().lower()
    reasoning_hash = hashlib.sha256(reasoning_str.encode()).hexdigest() if reasoning_str else None
    evidence_str = ""
    for ev in delivery.get("ac_evidence", []):
        evidence_str += (ev.get("evidence") or "").strip().lower() + "|"
    evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest() if evidence_str else None

    # Validate — P5.5: pass per-AC verification so the validator's file/test
    # rule stops over-rejecting command/manual ACs.
    ac_verif_map = {ac.position: ac.verification for ac in task.acceptance_criteria}
    result = validate_delivery(delivery, contract, task.type, prev_attempt_dict,
                               ac_verifications=ac_verif_map)

    # Phase A.3 shadow-mode comparator. Default mode='off' is a no-op
    # short-circuit; flip via FORGE_VERDICT_ENGINE_MODE=shadow once the
    # canary window opens. Disagreements -> verdict_divergences row.
    # Legacy `result` remains authoritative; this call NEVER raises.
    compare_and_log(
        session_factory=lambda: db,
        execution_id=execution.id,
        ctx=EvaluationContext(
            entity_type="execution",
            entity_id=execution.id,
            from_state="DELIVERED",
            to_state="VALIDATING",
            artifact={
                "delivery": delivery,
                "contract": contract,
                "task_type": task.type,
                "prev_attempt": prev_attempt_dict,
                "ac_verifications": ac_verif_map,
            },
            evidence=(),
        ),
        rules=(contract_validator_rule,),
        legacy_passed=result.all_pass,
        legacy_reason=getattr(result, "fix_instructions", None) or None,
    )

    # Duplicate detection: if current hash matches any previous attempt → WARNING
    for pa in prev_attempts:
        if reasoning_hash and pa.reasoning_hash == reasoning_hash:
            result.checks.append(CheckResult(
                "WARNING", "resubmit.identical_reasoning",
                f"Reasoning identical to attempt #{pa.attempt_number} ({pa.verdict})"
            ))
            break
    for pa in prev_attempts:
        if evidence_hash and pa.evidence_hash == evidence_hash:
            result.checks.append(CheckResult(
                "WARNING", "resubmit.identical_evidence",
                f"Evidence identical to attempt #{pa.attempt_number} ({pa.verdict})"
            ))
            break

    execution.delivery = delivery
    execution.delivered_at = dt.datetime.now(dt.timezone.utc)
    execution.validation_result = {
        "all_pass": result.all_pass,
        "checks": [{"status": c.status, "check": c.check, "detail": c.detail} for c in result.checks],
    }
    execution.validated_at = dt.datetime.now(dt.timezone.utc)

    # Record attempt (always, regardless of ACCEPTED/REJECTED)
    attempt_num = (prev_attempts[0].attempt_number + 1) if prev_attempts else 1
    db.add(ExecutionAttempt(
        execution_id=execution.id,
        attempt_number=attempt_num,
        verdict="ACCEPTED" if result.all_pass else "REJECTED",
        delivery_payload=delivery,
        validation_result=execution.validation_result,
        reasoning_hash=reasoning_hash,
        evidence_hash=evidence_hash,
    ))

    if result.all_pass:
        commit_status_transition(execution, entity_type="execution", target_state="ACCEPTED")
        execution.completed_at = dt.datetime.now(dt.timezone.utc)
        commit_status_transition(task, entity_type="task", target_state="DONE")
        task.completed_at = dt.datetime.now(dt.timezone.utc)

        # Save changes from delivery
        for ch in delivery.get("changes", []):
            ext_id = _next_external_id(db, task.project_id, "C")
            db.add(Change(
                project_id=task.project_id, execution_id=execution.id,
                external_id=ext_id, task_id=task.id,
                file_path=ch.get("file_path", ""), action=ch.get("action", "edit"),
                summary=ch.get("summary", ""), reasoning=ch.get("reasoning"),
            ))

        # Save decisions from delivery
        created_decisions: list[Decision] = []
        for dec in delivery.get("decisions", []):
            ext_id = _next_external_id(db, task.project_id, "D")
            d_row = Decision(
                project_id=task.project_id, execution_id=execution.id,
                external_id=ext_id, task_id=task.id,
                type=dec.get("type", "implementation"),
                issue=dec.get("issue", ""),
                recommendation=dec.get("recommendation", ""),
                reasoning=dec.get("reasoning"),
                status="CLOSED",
            )
            db.add(d_row)
            created_decisions.append(d_row)

        # Save findings from delivery
        for f in delivery.get("findings", []):
            ext_id = _next_external_id(db, task.project_id, "F")
            db.add(Finding(
                project_id=task.project_id, execution_id=execution.id,
                external_id=ext_id, type=f.get("type", "bug"),
                severity=f.get("severity", "MEDIUM"),
                title=f.get("title", ""),
                description=f.get("description", ""),
                file_path=f.get("file_path"),
                line_number=f.get("line_number"),
                evidence=f.get("evidence", ""),
                suggested_action=f.get("suggested_action"),
            ))

        _audit(db, task.project_id, "execution", execution.id, "accepted", f"agent:{execution.agent}",
               new_value={"task": task.external_id, "checks_passed": len(result.checks)})
        _audit(db, task.project_id, "task", task.id, "completed", "system",
               new_value={"ceremony": task.ceremony_level})

        db.commit()

        # CGAID artifact #5 — auto-export CLOSED ADRs to in-repo .ai/decisions/
        # Best-effort: filesystem is mirror, DB is source of truth.
        if created_decisions:
            try:
                from app.models import Project
                from app.services.adr_exporter import export_decision
                from app.config import settings as _settings
                proj = db.query(Project).filter(Project.id == task.project_id).first()
                if proj:
                    for d_row in created_decisions:
                        db.refresh(d_row)  # ensure external_id + created_at populated post-commit
                        export_decision(d_row, proj, _settings.workspace_root,
                                        task_ext_id=task.external_id)
            except Exception:
                pass

        return {
            "status": "ACCEPTED",
            "task_status": "DONE",
            "validation": execution.validation_result,
            "completion": {
                "changes_created": len(delivery.get("changes", [])),
                "decisions_created": len(delivery.get("decisions", [])),
                "findings_created": len(delivery.get("findings", [])),
            },
        }

    else:
        commit_status_transition(execution, entity_type="execution", target_state="REJECTED")
        execution.attempt_number += 1
        # Extend lease
        execution.lease_expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=15)

        _audit(db, task.project_id, "execution", execution.id, "rejected", "system",
               new_value={"attempt": execution.attempt_number, "failures": result.fix_instructions})

        db.commit()

        return {
            "status": "REJECTED",
            "attempt": execution.attempt_number,
            "validation": execution.validation_result,
            "fix_instructions": result.fix_instructions,
        }


# --- POST /execute/{id}/heartbeat ---

@router.post("/execute/{execution_id}/heartbeat")
def post_heartbeat(execution_id: int, db: Session = Depends(get_db)):
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(404, "Execution not found")

    if execution.status == "EXPIRED":
        raise HTTPException(410, "Execution expired")

    if execution.lease_renewals >= settings.max_lease_renewals:
        commit_status_transition(execution, entity_type="execution", target_state="EXPIRED")
        task = db.query(Task).filter(Task.id == execution.task_id).first()
        if task:
            commit_status_transition(task, entity_type="task", target_state="TODO")
            task.agent = None
        db.commit()
        raise HTTPException(410, f"Max renewals ({settings.max_lease_renewals}) exceeded")

    execution.lease_expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.lease_duration_minutes)
    execution.lease_renewals += 1
    db.commit()

    return {
        "lease_expires_at": execution.lease_expires_at.isoformat(),
        "renewals_remaining": settings.max_lease_renewals - execution.lease_renewals,
    }


# --- POST /execute/{id}/fail ---

@router.post("/execute/{execution_id}/fail")
def post_fail(execution_id: int, body: dict, db: Session = Depends(get_db)):
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(404, "Execution not found")

    reason = body.get("reason", "")
    if len(reason) < 50:
        raise HTTPException(422, "Reason must be >= 50 characters")

    commit_status_transition(execution, entity_type="execution", target_state="FAILED")
    task = db.query(Task).filter(Task.id == execution.task_id).first()
    if task:
        commit_status_transition(task, entity_type="task", target_state="FAILED")
        task.fail_reason = reason

    _audit(db, task.project_id if task else None, "execution", execution.id, "failed", f"agent:{execution.agent}",
           new_value={"reason": reason})

    db.commit()
    return {"task_status": "FAILED"}


# --- POST /execute/{id}/challenge ---

@router.post("/execute/{execution_id}/challenge")
def post_challenge(
    execution_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
):
    """Generate a challenge command for an accepted delivery.

    Auto-generates challenge questions from:
    - AC evidence vs actual AC text
    - Operational contract sections (assumptions, impact)
    - Agent memory patterns (if available)
    - Spec edge cases (if linked)

    Returns enriched challenge command ready for a challenger agent.
    """
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(404, "Execution not found")

    if execution.status != "ACCEPTED":
        raise HTTPException(409, f"Can only challenge ACCEPTED executions (current: {execution.status})")

    task = db.query(Task).filter(Task.id == execution.task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    delivery = execution.delivery or {}
    focus_areas = (body or {}).get("focus_areas", ["ac_verification", "impact_analysis", "edge_cases"])

    # --- Generate challenge questions from delivery ---
    questions = []

    # 1. Challenge each AC evidence claim
    ac_evidence = delivery.get("ac_evidence", [])
    for ac in task.acceptance_criteria:
        ev = next((e for e in ac_evidence if e.get("ac_index") == ac.position), None)
        if ev:
            questions.append(
                f"AC-{ac.position} claims '{ev.get('verdict')}': \"{ac.text[:80]}\"\n"
                f"   Evidence: \"{ev.get('evidence', '')[:100]}\"\n"
                f"   VERIFY: Read the actual {'test code at ' + ac.test_path if ac.test_path else 'implementation'}. "
                f"Does it ACTUALLY test what the AC says? Does it use mocks where it shouldn't?"
            )

    # 2. Challenge assumptions
    assumptions = delivery.get("assumptions", [])
    for a in assumptions:
        if not a.get("verified"):
            questions.append(
                f"ASSUMPTION (unverified): \"{a.get('statement', '')}\"\n"
                f"   If wrong: {a.get('if_wrong', 'unknown impact')}\n"
                f"   VERIFY: {a.get('verify_how', 'Check if this is actually true')}"
            )

    # 3. Challenge impact analysis gaps
    impact = delivery.get("impact_analysis", {})
    not_checked = impact.get("files_not_checked", [])
    for f in not_checked:
        questions.append(
            f"UNCHECKED FILE: {f.get('path', '?')}\n"
            f"   Reason not checked: {f.get('reason', '?')}\n"
            f"   Risk: {f.get('risk', '?')}\n"
            f"   VERIFY: Read this file. Does it import or depend on changed files?"
        )

    # 4. Challenge completion claims
    claims = delivery.get("completion_claims", {})
    for claim in claims.get("executed", []):
        questions.append(
            f"CLAIM: \"{claim.get('action', '')}\"\n"
            f"   Evidence: \"{claim.get('evidence', '')}\"\n"
            f"   Verified by: {claim.get('verified_by', 'not specified')}\n"
            f"   VERIFY: Run the verification command. Does output match evidence?"
        )
    for item in claims.get("not_executed", []):
        questions.append(
            f"NOT EXECUTED: \"{item.get('action', '')}\"\n"
            f"   Reason: {item.get('reason', '?')}\n"
            f"   Impact: {item.get('impact', '?')}\n"
            f"   VERIFY: Could this have been executed? Is the reason valid?"
        )

    # 5. Check changes vs reasoning consistency
    changes = delivery.get("changes", [])
    reasoning = delivery.get("reasoning", "")
    change_files = [c.get("file_path", "") for c in changes]
    unmentioned = [f for f in change_files if f.split("/")[-1].lower() not in reasoning.lower()]
    if unmentioned:
        questions.append(
            f"CONSISTENCY: Reasoning doesn't mention files: {unmentioned}\n"
            f"   VERIFY: Why were these files changed but not explained in reasoning?"
        )

    # --- Build challenge command ---
    challenge_command = (
        f"Challenge delivery of {task.external_id} ({task.name}).\n"
        f"Execution #{execution.id}, agent: {execution.agent}\n\n"
        f"INSTRUCTION: Verify EACH claim below. Read ACTUAL CODE, not declarations.\n"
        f"For each question: answer VERIFIED (with evidence) or REFUTED (with evidence).\n"
        f"Do NOT trust the delivery text — check the code and tests directly.\n\n"
        f"QUESTIONS:\n\n"
    )
    for i, q in enumerate(questions, 1):
        challenge_command += f"{i}. {q}\n\n"

    challenge_command += (
        f"OUTPUT FORMAT:\n"
        f"{{\n"
        f'  "findings": [\n'
        f'    {{"claim": "...", "verified": true/false, "evidence": "...", "severity": "HIGH/MEDIUM/LOW"}}\n'
        f"  ],\n"
        f'  "overall_verdict": "PASS/NEEDS_REWORK/FAIL"\n'
        f"}}\n"
    )

    # --- Enrich with reputation frame and micro-skills ---
    from app.services.prompt_parser import assemble_prompt
    # Create a temporary execution for the challenge
    challenge_exec = Execution(
        task_id=task.id,
        agent=(body or {}).get("challenger_agent", "challenger"),
        status="PROMPT_ASSEMBLED",
        lease_expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.lease_duration_minutes),
    )
    db.add(challenge_exec)
    db.flush()

    result = assemble_prompt(
        db, task, challenge_exec,
        raw_command=challenge_command,
        operation_type="challenge",
    )

    challenge_exec.prompt_text = result.prompt_text
    challenge_exec.prompt_hash = result.prompt_hash
    challenge_exec.prompt_meta = result.prompt_meta

    for sec in result.sections:
        sec.execution_id = challenge_exec.id
        db.add(sec)
    db.flush()

    section_map = {s.position: s.id for s in result.sections}
    for elem in result.elements:
        elem.execution_id = challenge_exec.id
        if elem.section_id == 0 and elem.position in section_map:
            elem.section_id = section_map[elem.position]
        elif elem.section_id == 0:
            elem.section_id = None
        db.add(elem)

    _audit(db, task.project_id, "execution", challenge_exec.id, "challenge_created", "system",
           new_value={"original_execution": execution.id, "questions": len(questions)})

    db.commit()

    return {
        "challenge_execution_id": challenge_exec.id,
        "original_execution_id": execution.id,
        "questions_count": len(questions),
        "enriched_command": result.prompt_text,
        "prompt_meta": result.prompt_meta,
    }
