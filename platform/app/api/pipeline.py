"""Pipeline API — ingest, analyze, orchestrate.

Full E2E flow:
1. /ingest  — upload source docs (SOW, emails, glossaries) → saved as Knowledge
2. /analyze — call Claude CLI to extract Objectives + KRs + conflicts from docs
3. /orchestrate — loop: claim task → Claude CLI in workspace → deliver → validate → next

Every Claude CLI invocation recorded in llm_calls table with cost/tokens/duration.
"""

import hashlib
import json
import os
import pathlib
import datetime as dt
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    Project, Task, AcceptanceCriterion, Knowledge, Objective, KeyResult,
    Decision, Execution, LLMCall, TestRun, Finding, OrchestrateRun,
)
from app.services.claude_cli import invoke_claude, CLIResult
from app.services.prompt_parser import assemble_prompt
from app.services.contract_validator import validate_delivery, CheckResult
from app.services.test_runner import verify_ac_tests, detect_language
from app.validation.rule_adapter import EvaluationContext
from app.validation.rules import contract_validator_rule, plan_gate_rule
from app.validation.shadow_comparator import compare_and_log
from app.validation.state_transition import commit_status_transition
from app.services.git_verify import ensure_repo, snapshot_head, commit_all, diff_report
from app.services.kr_measurer import measure_kr
from app.services.delivery_extractor import extract_from_delivery
from app.services.challenger import run_challenge
from app.services.workspace_infra import ensure_workspace_infra
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["pipeline"])


# ---------- Helpers ----------

def _project(db: Session, slug: str) -> Project:
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404, f"Project '{slug}' not found")
    return proj


def _resolve_anthropic_key(db: Session, project: Project) -> str | None:
    """Decrypt project's org Anthropic key. Returns None if no key set — subprocess
    falls back to system Claude CLI auth (dev-friendly).
    """
    if not project.organization_id:
        return None
    from app.models import Organization
    from app.services.auth import decrypt_secret
    org = db.query(Organization).filter(Organization.id == project.organization_id).first()
    if not org or not org.anthropic_api_key_encrypted:
        return None
    return decrypt_secret(org.anthropic_api_key_encrypted)


def _enforce_budget(db: Session, project: Project) -> None:
    """Hard stop — raise 402 Payment Required if org's current-month spend hit budget.
    Called BEFORE every LLM invocation.

    Returns silently if:
    - project has no org
    - org has no budget set
    - current month spend < budget
    """
    if not project.organization_id:
        return
    from app.models import Organization
    from sqlalchemy import func as _func
    # populate_existing() bypasses session identity cache — gets fresh budget from DB
    org = db.query(Organization).populate_existing().filter(
        Organization.id == project.organization_id
    ).first()
    if not org or org.budget_usd_monthly is None:
        return
    import datetime as _dt
    first = _dt.datetime.now(_dt.timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spend = db.query(_func.sum(LLMCall.cost_usd)).join(
        Project, Project.id == LLMCall.project_id
    ).filter(
        Project.organization_id == org.id,
        LLMCall.created_at >= first,
    ).scalar() or 0.0
    if float(spend) >= float(org.budget_usd_monthly):
        raise HTTPException(
            status_code=402,
            detail={
                "error": "monthly_budget_exceeded",
                "current_spend_usd": round(float(spend), 4),
                "budget_usd_monthly": float(org.budget_usd_monthly),
                "message": (
                    f"Organization '{org.slug}' has spent ${float(spend):.2f} this month, "
                    f"which meets/exceeds the budget of ${float(org.budget_usd_monthly):.2f}. "
                    f"Increase budget in Org settings to continue."
                ),
            },
        )


def _workspace(proj_slug: str) -> str:
    root = pathlib.Path(settings.workspace_root) / proj_slug / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


def _record_llm_call(
    db: Session,
    *,
    execution_id: int | None,
    project_id: int | None,
    purpose: str,
    prompt: str,
    workspace_dir: str,
    cli_result: CLIResult,
) -> LLMCall:
    rec = LLMCall(
        execution_id=execution_id,
        project_id=project_id,
        purpose=purpose,
        model=settings.claude_model,
        model_used=cli_result.model_used,
        session_id=cli_result.session_id,
        prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        prompt_chars=len(prompt),
        prompt_preview=prompt[:2000],
        full_prompt=prompt,
        response_text=cli_result.agent_response,
        response_chars=len(cli_result.agent_response or ""),
        return_code=cli_result.return_code,
        is_error=cli_result.is_error,
        api_error_status=cli_result.api_error_status,
        parse_error=cli_result.parse_error,
        stderr_tail=(cli_result.stderr or "")[-2000:] if cli_result.stderr else None,
        duration_ms=cli_result.duration_ms,
        cost_usd=cli_result.cost_usd,
        input_tokens=cli_result.input_tokens,
        output_tokens=cli_result.output_tokens,
        cache_read_tokens=cli_result.cache_read_tokens,
        workspace_dir=workspace_dir,
        delivery_parsed=cli_result.delivery,
    )
    db.add(rec)
    db.flush()
    return rec


def _next_external_id(db: Session, project_id: int, model, prefix: str) -> str:
    from sqlalchemy import func
    # Use autoflush to include pending inserts
    db.flush()
    max_id = db.query(func.max(model.external_id)).filter(
        model.project_id == project_id,
        model.external_id.like(f"{prefix}-%"),
    ).scalar()
    if not max_id:
        return f"{prefix}-001"
    try:
        num = int(max_id.split("-")[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f"{prefix}-{num:03d}"


# ---------- /ingest ----------

@router.post("/projects/{slug}/ingest")
async def ingest_documents(
    slug: str,
    request: Request,
    files: list[UploadFile] = File(...),
    category: str = Form("source-document"),
    db: Session = Depends(get_db),
):
    """Upload source documents (SOW, stakeholder emails, glossaries, NFR).

    Each file saved as Knowledge row with category=source-document (default).
    Returns list of created Knowledge external_ids.
    """
    # Rate-limit ingestion per-user to prevent storage abuse.
    # Gated behind FORGE_RATE_LIMIT_ENABLED=true so tests remain unaffected.
    import os as _os
    if _os.environ.get("FORGE_RATE_LIMIT_ENABLED", "").lower() in ("1", "true", "yes"):
        from app.services.rate_limit import check_rate_limit, RateLimitExceeded
        user = getattr(request.state, "user", None)
        user_id = user.id if user else "anon"
        try:
            check_rate_limit(
                key=f"ingest:user:{user_id}",
                max_per_window=20,      # 20 ingests
                window_sec=3600,        # per hour
            )
        except RateLimitExceeded as e:
            raise HTTPException(
                status_code=429,
                detail={"error": "too_many_requests", "retry_after": e.retry_after},
                headers={"Retry-After": str(e.retry_after)},
            )
    proj = _project(db, slug)
    # Decision #8-B: PII scanner runs in WARN posture on every ingest.
    # We do NOT block; we stamp pii_scan metadata on the Knowledge row
    # so the UI can show a badge + the audit log tracks findings.
    from app.services.pii_scanner import scan_then_decide
    created = []
    for f in files:
        raw = await f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("utf-8", errors="replace")

        # PII scan (fail-safe: wrap in try so a detector bug never breaks ingest)
        pii_meta = None
        try:
            findings, decision = scan_then_decide(
                content,
                # WARN posture: HIGH severity downgraded to 'warn', not 'block'
                high_severity_blocks=False,
                medium_severity_warns=True,
            )
            pii_meta = {
                "decision": decision,
                "findings_count": len(findings),
                "types": sorted({x.type for x in findings}),
            }
        except Exception:
            pii_meta = {"decision": "pass", "findings_count": 0, "types": [],
                        "error": "scanner failed — treated as clean"}

        ext_id = _next_external_id(db, proj.id, Knowledge, "SRC")
        k = Knowledge(
            project_id=proj.id,
            external_id=ext_id,
            title=f.filename or ext_id,
            category=category,
            content=content,
            scopes=[],
            source_type="upload",
            source_ref=f.filename,
            pii_scan=pii_meta,
        )
        db.add(k)
        db.flush()
        created.append({
            "id": k.id, "external_id": ext_id, "filename": f.filename,
            "chars": len(content),
            "pii_scan": pii_meta,  # surfaced in response so UI can show warning
        })
    db.commit()
    return {"ingested": len(created), "documents": created}


# ---------- /analyze ----------

ANALYZE_PROMPT_TEMPLATE = """Jesteś analitykiem biznesowym. Przeczytaj poniższe dokumenty źródłowe i wyciągnij z nich:

1. OBJECTIVES — cele biznesowe z mierzalnymi Key Results (KR)
2. CONFLICTS — sprzeczności między dokumentami (jeśli są)
3. OPEN_QUESTIONS — rzeczy których nie ma w dokumentach a są potrzebne do zaplanowania

Zasady:
- Każdy objective musi mieć MIN. 2 KR (jeden numeryczny i jeden descriptive)
- KR muszą być weryfikowalne (nie "dobry UX", tylko "response time < 200ms" lub "user can complete flow in < 3 clicks")
- Nie wymyślaj wymagań spoza dokumentów
- Jeżeli coś jest niejednoznaczne — dopisz do OPEN_QUESTIONS lub CONFLICTS

DOKUMENTY ŹRÓDŁOWE:

{source_docs}

ODPOWIEDŹ — czysty JSON, bez komentarza, bez markdown fence:

{{
  "objectives": [
    {{
      "external_id": "O-001",
      "title": "krótki tytuł",
      "business_context": "dlaczego to jest potrzebne, kto z tego korzysta, jaki problem rozwiązuje",
      "scopes": ["backend", "frontend", "database"],
      "priority": 1,
      "key_results": [
        {{"text": "measurable KR", "kr_type": "numeric", "target_value": 200, "measurement_command": "curl -w '%{{time_total}}'..."}},
        {{"text": "descriptive KR", "kr_type": "descriptive"}}
      ]
    }}
  ],
  "conflicts": [
    {{"issue": "X mówi A, Y mówi B", "documents_involved": ["SRC-001", "SRC-002"], "recommendation": "..."}}
  ],
  "open_questions": [
    {{"question": "...", "why_needed": "..."}}
  ]
}}
"""


@router.post("/projects/{slug}/analyze")
def analyze_documents(slug: str, db: Session = Depends(get_db)):
    """Call Claude CLI to extract Objectives + KRs + conflicts from ingested docs.

    Creates Objective + KeyResult entities. Conflicts become OPEN Decisions.
    """
    proj = _project(db, slug)
    docs = db.query(Knowledge).filter(
        Knowledge.project_id == proj.id,
        Knowledge.category.in_(["source-document", "feature-spec", "requirement"]),
        Knowledge.status == "ACTIVE",
    ).all()
    if not docs:
        raise HTTPException(422, "No source documents found. Call /ingest first.")

    # Build source doc bundle for prompt
    src_text = ""
    for d in docs:
        src_text += f"\n## {d.external_id} — {d.title}\n\n{d.content}\n\n---\n"

    prompt = ANALYZE_PROMPT_TEMPLATE.format(source_docs=src_text)
    # G3 — inject project's operational contract into the analyze prompt
    from app.api.tier1 import build_contract_injection
    prompt = build_contract_injection(proj) + prompt
    workspace = _workspace(slug)
    _enforce_budget(db, proj)
    anthropic_key = _resolve_anthropic_key(db, proj)

    cli = invoke_claude(
        prompt=prompt,
        workspace_dir=workspace,
        model=settings.claude_model,
        max_budget_usd=settings.claude_budget_per_task_usd,
        timeout_sec=settings.claude_timeout_sec,
        api_key=anthropic_key,
    )

    llm_call = _record_llm_call(
        db, execution_id=None, project_id=proj.id, purpose="analyze",
        prompt=prompt, workspace_dir=workspace, cli_result=cli,
    )
    db.commit()

    if cli.is_error or cli.parse_error:
        raise HTTPException(500, {
            "error": "Claude CLI failed",
            "parse_error": cli.parse_error,
            "cli_error": cli.is_error,
            "stderr_tail": (cli.stderr or "")[-500:],
            "llm_call_id": llm_call.id,
        })

    payload = cli.delivery or {}
    if "objectives" not in payload:
        raise HTTPException(500, {
            "error": "analyze response missing 'objectives' key",
            "llm_call_id": llm_call.id,
            "response_preview": cli.agent_response[:500],
        })

    # Create objectives + KRs
    created_objectives = []
    for o in payload.get("objectives", []):
        obj = Objective(
            project_id=proj.id,
            external_id=o.get("external_id") or _next_external_id(db, proj.id, Objective, "O"),
            title=o.get("title", "untitled"),
            business_context=o.get("business_context", ""),
            scopes=o.get("scopes", []),
            priority=o.get("priority", 3),
        )
        db.add(obj)
        db.flush()
        for i, kr in enumerate(o.get("key_results", [])):
            db.add(KeyResult(
                objective_id=obj.id,
                position=i,
                text=kr.get("text", ""),
                kr_type=kr.get("kr_type", "descriptive"),
                target_value=kr.get("target_value"),
                measurement_command=kr.get("measurement_command"),
            ))
        created_objectives.append({"id": obj.id, "external_id": obj.external_id, "kr_count": len(o.get("key_results", []))})

    # Create conflicts as OPEN decisions
    created_conflicts = []
    for c in payload.get("conflicts", []):
        ext_id = _next_external_id(db, proj.id, Decision, "D")
        d = Decision(
            project_id=proj.id,
            external_id=ext_id,
            type="conflict",
            issue=c.get("issue", ""),
            recommendation=c.get("recommendation", ""),
            reasoning=f"Documents: {', '.join(c.get('documents_involved', []))}",
            status="OPEN",
            severity="HIGH",
        )
        db.add(d)
        db.flush()
        created_conflicts.append(ext_id)

    # Open questions as OPEN decisions too
    created_questions = []
    for q in payload.get("open_questions", []):
        ext_id = _next_external_id(db, proj.id, Decision, "D")
        d = Decision(
            project_id=proj.id,
            external_id=ext_id,
            type="open_question",
            issue=q.get("question", ""),
            recommendation=q.get("why_needed", ""),
            status="OPEN",
            severity="MEDIUM",
        )
        db.add(d)
        created_questions.append(ext_id)

    db.commit()

    return {
        "objectives_created": created_objectives,
        "conflicts_created": created_conflicts,
        "open_questions_created": created_questions,
        "llm_call_id": llm_call.id,
        "cost_usd": cli.cost_usd,
        "duration_ms": cli.duration_ms,
    }


# ---------- /plan (via LLM) ----------

PLAN_PROMPT_TEMPLATE = """Jesteś tech leadem. Masz objective biznesowy i musisz rozłożyć go na sekwencję zadań implementacyjnych.

OBJECTIVE: {obj_ext} — {obj_title}
Context: {obj_context}
Scopes: {obj_scopes}

Key Results (wszystkie muszą być pokryte przez zadania):
{kr_list}

Dokumenty źródłowe (dla szczegółów):
{source_docs}

Zasady:
- Każde zadanie typu feature/bug MUSI mieć min. 1 acceptance criteria z verification: "test" lub "command"
- AC musi mieć scenario_type: positive|negative|edge_case|regression — min. 1 negative lub edge_case
- Zadania ułożone w sensownej kolejności (depends_on), max 15 zadań
- Każde zadanie musi mieć konkretną instrukcję (co zrobić, jakie pliki zmienić, jaki endpoint dodać)
- origin musi być = "{obj_ext}"
- produces: semantyczny kontrakt dla następnych zadań (np. endpoint shape)
- **requirement_refs**: lista konkretnych referencji z dokumentów źródłowych które ten task implementuje (np. ["SRC-001 §2.4", "SRC-002 punkt 3"]) — obowiązkowe dla feature/bug
- **completes_kr_ids**: lista KR które ten task domyka (np. ["KR0"]) — tylko gdy task faktycznie realizuje weryfikowalną część KR, inaczej []

ODPOWIEDŹ — czysty JSON bez markdown:

{{
  "tasks": [
    {{
      "external_id": "T-001",
      "name": "krótka nazwa",
      "instruction": "pełna instrukcja co zrobić",
      "type": "feature",
      "origin": "{obj_ext}",
      "scopes": ["backend"],
      "depends_on": [],
      "produces": {{"endpoint": "POST /x → 201 {{id}}"}},
      "requirement_refs": ["SRC-001 §2.4"],
      "completes_kr_ids": ["KR0"],
      "acceptance_criteria": [
        {{"text": "...min 20 chars...", "scenario_type": "positive", "verification": "test", "test_path": "tests/test_x.py::test_ok"}},
        {{"text": "...min 20 chars...", "scenario_type": "negative", "verification": "test", "test_path": "tests/test_x.py::test_err"}}
      ]
    }}
  ]
}}
"""


class PlanRequest(BaseModel):
    objective_external_id: str


@router.post("/projects/{slug}/plan")
def plan_from_objective(slug: str, body: PlanRequest, db: Session = Depends(get_db)):
    """Call Claude CLI to decompose objective into tasks graph."""
    proj = _project(db, slug)
    obj = db.query(Objective).filter(
        Objective.project_id == proj.id,
        Objective.external_id == body.objective_external_id,
    ).first()
    if not obj:
        raise HTTPException(404, f"Objective {body.objective_external_id} not found")

    krs = db.query(KeyResult).filter(KeyResult.objective_id == obj.id).order_by(KeyResult.position).all()
    kr_text = "\n".join([f"- KR{kr.position}: {kr.text} ({kr.kr_type}, target={kr.target_value})" for kr in krs])

    docs = db.query(Knowledge).filter(
        Knowledge.project_id == proj.id,
        Knowledge.category.in_(["source-document", "feature-spec", "requirement"]),
    ).all()
    src_bundle = "\n".join([f"### {d.external_id}: {d.title}\n{d.content[:3000]}" for d in docs])

    prompt = PLAN_PROMPT_TEMPLATE.format(
        obj_ext=obj.external_id,
        obj_title=obj.title,
        obj_context=obj.business_context,
        obj_scopes=obj.scopes,
        kr_list=kr_text,
        source_docs=src_bundle,
    )
    # G3 — inject project's operational contract into the planning prompt
    from app.api.tier1 import build_contract_injection
    prompt = build_contract_injection(proj) + prompt
    workspace = _workspace(slug)
    _enforce_budget(db, proj)
    anthropic_key = _resolve_anthropic_key(db, proj)

    cli = invoke_claude(
        prompt=prompt,
        workspace_dir=workspace,
        model=settings.claude_model,
        max_budget_usd=settings.claude_budget_per_task_usd,
        timeout_sec=settings.claude_timeout_sec,
        api_key=anthropic_key,
    )

    llm_call = _record_llm_call(
        db, execution_id=None, project_id=proj.id, purpose="plan",
        prompt=prompt, workspace_dir=workspace, cli_result=cli,
    )
    db.commit()

    if cli.is_error or cli.parse_error or not cli.delivery:
        raise HTTPException(500, {"parse_error": cli.parse_error, "preview": cli.agent_response[:500], "llm_call_id": llm_call.id})

    tasks_data = cli.delivery.get("tasks", [])
    if not tasks_data:
        raise HTTPException(500, {"error": "no tasks in response", "llm_call_id": llm_call.id})

    # P5.3 — block plan that doesn't trace tasks back to source docs.
    # Determined by: does the project hold any source-doc Knowledge entries?
    # If yes, every feature/bug/develop task in this plan MUST declare requirement_refs.
    has_sources = bool(docs)  # `docs` was loaded above for the prompt
    from app.services.plan_gate import validate_plan_requirement_refs
    ref_violations = validate_plan_requirement_refs(
        tasks_data, project_has_source_docs=has_sources,
    )

    # Phase A.3 shadow-mode comparator. Mode='off' is a no-op; flip to
    # 'shadow' once canary opens. This call NEVER raises.
    # NOTE: no execution_id at plan-gate time (plan precedes Execution);
    # using project_id as the divergence FK target is incorrect for the
    # current schema (verdict_divergences.execution_id NOT NULL). Skip
    # logging here until A.4 wiring decides on a Plan-level entity FK.
    # The shadow call is left commented to mark the integration point
    # without inserting bad data. Tracked in commit body.
    # compare_and_log(
    #     session_factory=lambda: db,
    #     execution_id=...,  # NEEDS: Plan entity or proj-level audit row
    #     ctx=EvaluationContext(
    #         entity_type="plan",
    #         entity_id=proj.id,
    #         from_state="__init__",
    #         to_state="VALIDATED",
    #         artifact={
    #             "tasks_data": tasks_data,
    #             "project_has_source_docs": has_sources,
    #         },
    #         evidence=(),
    #     ),
    #     rules=(plan_gate_rule,),
    #     legacy_passed=(not ref_violations),
    #     legacy_reason="; ".join(ref_violations) if ref_violations else None,
    # )

    if ref_violations:
        raise HTTPException(400, {
            "error": "plan_traceability_gate: tasks missing requirement_refs",
            "violations": ref_violations,
            "llm_call_id": llm_call.id,
            "hint": (
                "The project has ingested source documents — every feature/bug/develop "
                "task must reference back to at least one SRC-NNN fragment so the user "
                "can audit which requirement each task actually implements."
            ),
        })

    # Create tasks — remap Claude's planning-scoped IDs to unique project-wide IDs
    # (Claude generates T-001..T-0NN per plan call; collides if earlier objectives already used those)
    existing_ids = {t.external_id for t in db.query(Task).filter(Task.project_id == proj.id).all()}
    planning_id_to_real: dict[str, str] = {}
    ext_id_to_task: dict[str, Task] = {}
    created = []
    for t_data in tasks_data:
        planning_id = t_data.get("external_id") or ""
        if planning_id and planning_id not in existing_ids and planning_id not in planning_id_to_real.values():
            real_id = planning_id
        else:
            real_id = _next_external_id(db, proj.id, Task, "T")
        planning_id_to_real[planning_id] = real_id
        existing_ids.add(real_id)

        t = Task(
            project_id=proj.id,
            external_id=real_id,
            name=t_data.get("name", "untitled"),
            instruction=t_data.get("instruction"),
            type=t_data.get("type", "feature"),
            scopes=t_data.get("scopes", []),
            origin=t_data.get("origin", obj.external_id),
            produces=t_data.get("produces"),
            requirement_refs=t_data.get("requirement_refs"),
            completes_kr_ids=t_data.get("completes_kr_ids"),
        )
        db.add(t)
        db.flush()
        ext_id_to_task[planning_id] = t  # key by Claude's planning ID for dep resolution
        for i, ac in enumerate(t_data.get("acceptance_criteria", [])):
            text = ac.get("text", "")
            if len(text) < 20:
                text = text.ljust(20, ".")
            db.add(AcceptanceCriterion(
                task_id=t.id,
                position=i,
                text=text,
                scenario_type=ac.get("scenario_type", "positive"),
                verification=ac.get("verification", "manual"),
                test_path=ac.get("test_path"),
                command=ac.get("command"),
            ))
        created.append({"id": t.id, "external_id": t.external_id})

    # Resolve dependencies using Claude's planning IDs
    for t_data in tasks_data:
        for dep_ext in t_data.get("depends_on", []) or []:
            t = ext_id_to_task.get(t_data["external_id"])
            dep = ext_id_to_task.get(dep_ext)
            if t and dep:
                t.dependencies.append(dep)

    db.commit()

    return {
        "tasks_created": created,
        "llm_call_id": llm_call.id,
        "cost_usd": cli.cost_usd,
        "duration_ms": cli.duration_ms,
    }


# ---------- /orchestrate ----------

EXECUTE_SUFFIX = """

---

## KRYTYCZNE: FORMAT ODPOWIEDZI

**Każda odpowiedź MUSI kończyć się blokiem JSON w dokładnie tym formacie.** Nawet jeśli nie mogłeś ukończyć zadania — i tak MUSISZ zwrócić JSON z opisem czego nie zrobiłeś w `completion_claims.not_executed`. NIE piszemy instrukcji dla użytkownika — piszemy DELIVERY.

JAK PISAĆ EVIDENCE:
- Każdy AC musi mieć UNIKALNE evidence opisujące KONKRETNE zachowanie które zostało zweryfikowane.
- NIE kopiuj struktury "tests/X.py::test_Y PASSED — opis" — po opisie MUSI być unikalna treść (np. konkretna wartość z assertion, konkretny error message, konkretna liczba rekordów).
- Im bardziej specyficzne evidence per AC, tym lepiej.

FORMAT ODPOWIEDZI (MUSISZ zakończyć TYM JSONEM jako ostatni blok):

```json
{
  "reasoning": "co zrobiłeś i dlaczego, z odniesieniami do ścieżek plików, min 100 znaków",
  "ac_evidence": [
    {"ac_index": 0, "verdict": "PASS", "evidence": "konkretne: ścieżka pliku lub polecenie i jego output [EXECUTED]", "scenario_type": "positive"}
  ],
  "assumptions": [
    {"statement": "co założyłeś", "verified": false, "if_wrong": "co się stanie", "verify_how": "jak sprawdzić"}
  ],
  "impact_analysis": {
    "files_changed": ["konkretne/ściezki.py"],
    "files_not_checked": []
  },
  "changes": [
    {"file_path": "app/x.py", "action": "create|edit|delete", "summary": "min 20 znaków, unikalne per plik"}
  ],
  "completion_claims": {
    "executed": [{"action": "...", "evidence": "...", "verified_by": "..."}],
    "not_executed": [],
    "conclusion": "..."
  }
}
```

Wymagania:
- Musisz FAKTYCZNIE edytować pliki (masz Write/Edit tools)
- Musisz uruchomić testy jeżeli AC ma verification=test
- Oznacz claims [EXECUTED] (uruchomiłeś), [INFERRED] (przeczytałeś kod), [ASSUMED] (zgadłeś)
- Jeżeli czegoś nie zrobiłeś — wpisz w completion_claims.not_executed
"""


class OrchestrateRequest(BaseModel):
    max_tasks: int | None = None
    max_retries_per_task: int | None = None
    stop_on_failure: bool = True
    skip_infra: bool = False
    enable_redis: bool = False


def _run_orchestrate_background(slug: str, params: dict, run_id: int):
    """Background worker — runs full orchestrate with own DB session.
    Updates orchestrate_runs row throughout via _update_run.
    """
    from app.database import SessionLocal as _SL
    db = _SL()
    try:
        body = OrchestrateRequest(**params)
        _update_run(db, run_id, status="RUNNING")
        try:
            orchestrate(slug, body, db, run_id=run_id)
        except HTTPException as ex:
            _update_run(db, run_id, status="BUDGET_EXCEEDED" if ex.status_code == 402 else "FAILED",
                        error=str(ex.detail), finished_at=dt.datetime.now(dt.timezone.utc))
        except Exception as ex:
            _update_run(db, run_id, status="FAILED",
                        error=f"{type(ex).__name__}: {str(ex)[:500]}",
                        finished_at=dt.datetime.now(dt.timezone.utc))
    finally:
        db.close()


def _update_run(db: Session, run_id: int | None, **fields):
    """Helper — update orchestrate_runs row inline (best-effort, ignore if no run_id).
    P5.7: always bump `updated_at` so orphan-recovery can distinguish an active worker
    (row mutating) from a dead one (row frozen). Bulk-update doesn't fire `onupdate`
    hooks, so we set it explicitly."""
    if not run_id:
        return
    fields.setdefault("updated_at", dt.datetime.now(dt.timezone.utc))
    db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).update(fields)
    db.commit()


def _check_cancel(db: Session, run_id: int | None) -> bool:
    if not run_id:
        return False
    row = db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).first()
    return bool(row and row.cancel_requested)


def _check_pause(db: Session, run_id: int | None) -> bool:
    """P1.1 — cooperative pause. Fresh read so executor reacts to recent UI click."""
    if not run_id:
        return False
    db.expire_all()
    row = db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).first()
    return bool(row and row.pause_requested)


@router.post("/projects/{slug}/orchestrate")
def orchestrate(
    slug: str,
    body: OrchestrateRequest | None = None,
    db: Session = Depends(get_db),
    run_id: int | None = None,
):
    """Run orchestration loop until no more tasks or limits hit.

    Loop per task:
      1. Find next TODO with met deps, claim it (status=IN_PROGRESS)
      2. Assemble prompt via prompt_parser (P0-P99 + operational contract)
      3. Append EXECUTE_SUFFIX with delivery format
      4. Invoke Claude CLI in project workspace
      5. Parse delivery → validate → if REJECTED retry up to max_retries with fix_instructions
      6. If ACCEPTED → mark DONE, next task
    """
    body = body or OrchestrateRequest()
    max_tasks = body.max_tasks or settings.orchestrator_max_tasks
    max_retries = body.max_retries_per_task or settings.orchestrator_max_retries_per_task

    proj = _project(db, slug)
    workspace = _workspace(slug)
    results = []
    total_cost = 0.0
    # Ensure workspace is a git repo (for diff verification)
    ensure_repo(workspace)

    # Phase W4: resolve org's Anthropic key once per orchestrate run.
    # Wrapped invoke_fn used by Phase B (extract) + Phase C (challenge).
    anthropic_key_orchestrate = _resolve_anthropic_key(db, proj)
    from functools import partial as _partial
    invoke_claude_with_key = _partial(invoke_claude, api_key=anthropic_key_orchestrate)

    # Phase C: ensure isolated workspace infrastructure (postgres + optional redis)
    infra_env: dict[str, str] = {}
    infra_info: dict = {"skipped": True}
    if not body.skip_infra:
        infra = ensure_workspace_infra(workspace, slug, enable_redis=body.enable_redis)
        infra_info = {
            "started": infra.started,
            "postgres_port": infra.postgres_port,
            "redis_port": infra.redis_port,
            "database_url_masked": infra.database_url.replace(
                infra.database_url.split(":")[2].split("@")[0], "***"
            ) if infra.database_url else None,
            "error": infra.error,
        }
        if infra.started:
            infra_env = dict(infra.env)

        # P5.1 — install workspace Python deps so pytest doesn't ImportError
        # on packages Claude listed in requirements.txt (e.g. locust, factory_boy).
        from app.services.workspace_infra import install_workspace_deps
        deps = install_workspace_deps(workspace)
        infra_info["deps"] = {
            "attempted": deps.attempted,
            "installed": deps.installed,
            "duration_sec": round(deps.duration_sec, 1),
            "return_code": deps.return_code,
            "error": deps.error,
            "stderr_tail": deps.stderr_tail[-400:] if deps.stderr_tail else "",
        }
        # If pip failed, surface as a finding-equivalent so the user notices —
        # but don't abort the whole orchestrate (some tasks may not need the deps).
        if deps.attempted and not deps.installed:
            try:
                ext_id = _next_external_id(db, proj.id, Finding, "F")
                db.add(Finding(
                    project_id=proj.id, external_id=ext_id,
                    type="risk", severity="HIGH",
                    title=f"Workspace deps install failed (rc={deps.return_code})",
                    description=(
                        f"`pip install -r {deps.file_path}` failed during orchestrate setup. "
                        f"Tests that depend on these packages will ImportError and fail the gate. "
                        f"stderr tail: {(deps.stderr_tail or '')[:500]}"
                    ),
                    suggested_action="Check requirements.txt for typos / missing pins; re-run orchestrate.",
                    evidence=f"forge/workspace_infra.install_workspace_deps return_code={deps.return_code}",
                ))
                db.commit()
            except Exception:
                db.rollback()  # finding logging shouldn't crash orchestrate

    for _iter in range(max_tasks):
        # Find next TODO with deps met
        todo_tasks = db.query(Task).filter(
            Task.project_id == proj.id,
            Task.status == "TODO",
        ).order_by(Task.id).all()

        done_ids = {
            t.id for t in db.query(Task).filter(
                Task.project_id == proj.id,
                Task.status.in_(("DONE", "SKIPPED")),
            ).all()
        }

        candidate = None
        for t in todo_tasks:
            if not t.dependencies or {d.id for d in t.dependencies}.issubset(done_ids):
                candidate = t
                break
        if not candidate:
            break

        # Cooperative cancel check
        if _check_cancel(db, run_id):
            _update_run(db, run_id, status="CANCELLED",
                        progress_message="Cancelled by user request",
                        finished_at=dt.datetime.now(dt.timezone.utc))
            return {"tasks_run": len(results), "results": results,
                    "total_cost_usd": round(total_cost, 4),
                    "workspace": workspace, "workspace_infra": infra_info,
                    "stopped_reason": "cancelled"}

        # P1.1 — cooperative pause check BEFORE claiming the next task.
        # On pause: current task stays TODO (we haven't claimed yet); resume picks up here.
        # finished_at stays NULL so the run is distinguishable from DONE/CANCELLED.
        if _check_pause(db, run_id):
            _update_run(db, run_id, status="PAUSED",
                        paused_at=dt.datetime.now(dt.timezone.utc),
                        current_phase="paused",
                        progress_message=f"Paused after {len(results)} task(s); POST /resume to continue")
            return {"tasks_run": len(results), "results": results,
                    "total_cost_usd": round(total_cost, 4),
                    "workspace": workspace, "workspace_infra": infra_info,
                    "stopped_reason": "paused"}

        # Claim
        commit_status_transition(candidate, entity_type="task", target_state="IN_PROGRESS")
        candidate.agent = "orchestrator-cli"
        candidate.started_at = dt.datetime.now(dt.timezone.utc)
        _update_run(db, run_id,
                    current_task_external_id=candidate.external_id,
                    current_phase="claim",
                    progress_message=f"Claimed task {candidate.external_id} ({candidate.name[:80]})")
        ac_count = len(candidate.acceptance_criteria)
        ceremony = "LIGHT" if (candidate.type in ("chore", "investigation") or ac_count <= 1) else ("STANDARD" if ac_count <= 3 else "FULL")
        candidate.ceremony_level = ceremony

        # Create execution
        execution = Execution(
            task_id=candidate.id,
            agent="orchestrator-cli",
            status="PROMPT_ASSEMBLED",
            lease_expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.lease_duration_minutes),
        )
        db.add(execution)
        db.flush()

        # Assemble prompt
        asm = assemble_prompt(db, candidate, execution, operation_type="implement")
        execution.prompt_text = asm.prompt_text
        execution.prompt_hash = asm.prompt_hash
        execution.prompt_meta = asm.prompt_meta
        for sec in asm.sections:
            sec.execution_id = execution.id
            db.add(sec)
        db.flush()
        section_map = {s.position: s.id for s in asm.sections}
        for el in asm.elements:
            el.execution_id = execution.id
            if el.section_id == 0 and el.position in section_map:
                el.section_id = section_map[el.position]
            elif el.section_id == 0:
                el.section_id = None
            db.add(el)
        db.commit()

        # Minimal contract for validation (since we're bypassing output_contracts table lookup here)
        contract_def = {
            "required": {
                "reasoning": {"min_length": 100, "must_reference_file": True, "must_contain_why": True},
                "ac_evidence": {"min_length": 50, "must_reference_file_or_test": True, "fail_blocks": True},
            },
            "optional": {"changes": {"min_summary_length": 20, "unique_summaries": True}},
            "anti_patterns": {"copy_paste_evidence": True, "duplicate_summaries_threshold": 0.8},
        }
        execution.contract = contract_def
        db.commit()

        # Snapshot git HEAD before task starts (for diff verification later)
        head_before_sha, head_before_err = snapshot_head(workspace)

        # Retry loop
        task_attempts = []
        accepted = False
        fix_hint = ""
        for attempt in range(1, max_retries + 1):
            _update_run(db, run_id,
                        current_phase=f"execute (attempt {attempt}/{max_retries})",
                        progress_message=f"{candidate.external_id}: Claude CLI executing... (attempt {attempt})")
            # Auto-attach skills based on task context (F6)
            try:
                from app.services.skill_attach import TaskContext as _SkillCtx, resolve_skills, record_invocations
                _ctx = _SkillCtx(
                    project_id=proj.id,
                    task_type=candidate.type,
                    phase="execute",
                    files_touched=None,
                    language=None,
                )
                _attached = resolve_skills(db, _ctx)
                _skill_block = ""
                if _attached:
                    _parts = ["\n\n## Attached skills (auto-evaluated):\n"]
                    for sk in _attached[:6]:  # cap to 6
                        _parts.append(f"### [{sk.category}] {sk.name}\n{sk.prompt_text[:600]}\n")
                    _skill_block = "".join(_parts)
                    record_invocations(db, proj.id, _attached)
            except Exception:
                _skill_block = ""
            full_prompt = asm.prompt_text + _skill_block + EXECUTE_SUFFIX
            # DOC task execution path — prepend a tech-writer persona + output contract
            # aligned with mockup 10 (ADR / API ref / runbook)
            if candidate.type == "documentation":
                doc_directive = (
                    "\n\n## DOCUMENTATION TASK DIRECTIVE\n"
                    "You are a technical writer. Do NOT write code. Instead produce markdown documentation.\n"
                    "Use Michael-Nygard ADR format when the task asks for decision records:\n"
                    "  ## Status · ## Context · ## Decision · ## Alternatives · ## Consequences\n"
                    "Cite SRC-XXX where appropriate. For API reference, list endpoints with "
                    "method + path + request/response shape. End with NOT_CHECKED: listing assumptions.\n"
                )
                full_prompt = asm.prompt_text + _skill_block + doc_directive + EXECUTE_SUFFIX
            if fix_hint:
                full_prompt += (
                    f"\n\n---\n\nPOPRZEDNIA PRÓBA BYŁA ODRZUCONA.\n"
                    f"Co trzeba naprawić: {fix_hint}\n\n"
                    f"WAŻNE: odpowiedź MUSI być JSON w formacie wyżej. "
                    f"Jeśli nie możesz czegoś wykonać, wpisz to w `completion_claims.not_executed` "
                    f"ZAMIAST pisać instrukcje w tekście.\n"
                )

            try:
                _enforce_budget(db, proj)
            except HTTPException as ex:
                # Budget hit during orchestration — stop loop, mark task back to TODO
                commit_status_transition(candidate, entity_type="task", target_state="TODO")
                candidate.agent = None
                candidate.started_at = None
                commit_status_transition(execution, entity_type="execution", target_state="FAILED")
                db.commit()
                results.append({
                    "task": candidate.external_id,
                    "status": "BUDGET_EXCEEDED",
                    "detail": ex.detail,
                })
                _update_run(db, run_id, status="BUDGET_EXCEEDED",
                            error=str(ex.detail),
                            progress_message=f"{candidate.external_id}: budget exceeded — stopped",
                            finished_at=dt.datetime.now(dt.timezone.utc))
                return {
                    "tasks_run": len(results),
                    "results": results,
                    "total_cost_usd": round(total_cost, 4),
                    "workspace": workspace,
                    "workspace_infra": infra_info,
                    "stopped_reason": "monthly_budget_exceeded",
                }

            # E1 — Crafted mode: if project.config['execution_mode'] == 'crafted',
            # run a crafter LLM first to produce a detailed executor prompt.
            exec_mode = "direct"
            crafter_llm_id = None
            if (proj.config or {}).get("execution_mode") == "crafted":
                from app.services.crafter import craft_executor_prompt
                _update_run(db, run_id,
                            current_phase=f"crafter (attempt {attempt}/{max_retries})",
                            progress_message=f"{candidate.external_id}: crafter writing detailed prompt...")
                craft = craft_executor_prompt(
                    seed_prompt=full_prompt, workspace_dir=workspace,
                    model="opus", api_key=_resolve_anthropic_key(db, proj),
                    max_budget_usd=2.0, timeout_sec=300,
                )
                # Record the crafter's LLM call
                crafter_record = _record_llm_call(
                    db, execution_id=execution.id, project_id=proj.id,
                    purpose="craft", prompt=full_prompt, workspace_dir=workspace,
                    cli_result=craft.crafter_call,
                )
                total_cost += craft.crafter_call.cost_usd or 0.0
                crafter_llm_id = crafter_record.id
                exec_mode = "crafted"
                # Use the crafter's output as the executor prompt
                full_prompt = craft.executor_prompt + "\n\n" + EXECUTE_SUFFIX
                db.commit()

            execution.mode = exec_mode
            execution.crafter_call_id = crafter_llm_id
            db.commit()

            cli = invoke_claude(
                prompt=full_prompt,
                workspace_dir=workspace,
                model=settings.claude_model,
                max_budget_usd=settings.claude_budget_per_task_usd,
                timeout_sec=settings.claude_timeout_sec,
                api_key=_resolve_anthropic_key(db, proj),
            )
            total_cost += cli.cost_usd or 0.0

            llm_call = _record_llm_call(
                db, execution_id=execution.id, project_id=proj.id,
                purpose="execute", prompt=full_prompt, workspace_dir=workspace, cli_result=cli,
            )
            db.commit()

            if cli.is_error or not cli.delivery:
                task_attempts.append({"attempt": attempt, "error": cli.parse_error or "cli_error", "llm_call_id": llm_call.id})
                fix_hint = f"Previous response could not be parsed as JSON delivery. Error: {cli.parse_error}. Respond with EXACTLY the JSON format specified."
                continue

            delivery = cli.delivery
            # P5.5 — pass per-AC verification map so the validator stops demanding
            # file/test refs for command/manual ACs.
            ac_verif_map = {ac.position: ac.verification for ac in candidate.acceptance_criteria}
            val = validate_delivery(delivery, contract_def, candidate.type, None,
                                    ac_verifications=ac_verif_map)

            # Phase A.3 shadow-mode comparator. Mode='off' default = no-op.
            # Logs to verdict_divergences only on engine-vs-legacy disagree.
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
                        "contract": contract_def,
                        "task_type": candidate.type,
                        "prev_attempt": None,
                        "ac_verifications": ac_verif_map,
                    },
                    evidence=(),
                ),
                rules=(contract_validator_rule,),
                legacy_passed=val.all_pass,
                legacy_reason=getattr(val, "fix_instructions", None) or None,
            )
            execution.delivery = delivery
            execution.validation_result = {
                "all_pass": val.all_pass,
                "checks": [{"status": c.status, "check": c.check, "detail": c.detail} for c in val.checks],
            }
            execution.delivered_at = dt.datetime.now(dt.timezone.utc)

            task_attempts.append({
                "attempt": attempt, "accepted": val.all_pass,
                "fails": [c.check for c in val.checks if c.status == "FAIL"],
                "llm_call_id": llm_call.id, "cost_usd": cli.cost_usd,
            })

            if val.all_pass:
                # ------ VERIFICATION PHASE (Forge-owned, not trust-based) ------
                verification_issues: list[str] = []
                verification_report: dict = {}

                # 1. Git diff verify — commit + compare declared vs actual changes
                # Assisted-by trailer (Linux Kernel 2026 precedent): AI cannot use
                # legally-binding Signed-off-by; human accountability stays with the
                # reviewer/merger. Forge credits the AI model that wrote the diff.
                from app.services.git_verify import build_assisted_by_trailer
                # BUGFIX (2026-04-19 autonomous session): was `val.model_used` but
                # ValidationResult has no such attr — the CLIResult (cli) does.
                # Never triggered before because round-1 never passed validation
                # to reach this branch; P5.5 fix made the path reachable, exposing this.
                _trailer = build_assisted_by_trailer(
                    model_used=cli.model_used if cli else settings.claude_model,
                    task_ext_id=candidate.external_id,
                    execution_id=execution.id,
                    attempt=attempt,
                )
                head_after_sha, commit_err = commit_all(
                    workspace,
                    f"T-{candidate.external_id} attempt {attempt}",
                    trailer=_trailer,
                )
                if commit_err:
                    verification_issues.append(f"git_commit: {commit_err}")
                if head_before_sha and head_after_sha:
                    diff_rep = diff_report(workspace, head_before_sha, delivery.get("changes", []))
                    verification_report["git_diff"] = {
                        "head_before": diff_rep.head_before,
                        "head_after": diff_rep.head_after,
                        "actual_changes": diff_rep.actual_changes,
                        "undeclared": diff_rep.undeclared_files,
                        "phantom": diff_rep.phantom_files,
                        "summary": diff_rep.summary,
                    }
                    if diff_rep.phantom_files:
                        verification_issues.append(
                            f"phantom_files: declared but not changed: {diff_rep.phantom_files}"
                        )
                    # undeclared files → WARNING only (Claude may create legitimate support files)

                _update_run(db, run_id, current_phase="verify",
                            progress_message=f"{candidate.external_id}: running pytest + git diff + KR measurement")
                # 2. Test execution — Forge runs AC tests itself
                lang = detect_language(workspace)
                verification_report["language"] = lang
                test_verify = verify_ac_tests(
                    workspace,
                    candidate.acceptance_criteria,
                    env_extra=infra_env or None,
                    task_type=candidate.type,
                )
                verification_report["tests"] = {
                    "language": test_verify.get("language"),
                    "all_pass": test_verify.get("all_pass"),
                    "ac_results": test_verify.get("ac_results"),
                    "skipped": test_verify.get("skipped"),
                }
                # Persist test_runs row
                run_obj = test_verify.get("run")
                if run_obj is not None:
                    tr = TestRun(
                        execution_id=execution.id, project_id=proj.id,
                        language=lang or "unknown",
                        workspace_dir=workspace,
                        test_paths=[ac.test_path for ac in candidate.acceptance_criteria
                                    if ac.verification in ("test","command") and ac.test_path],
                        return_code=run_obj.return_code, duration_ms=run_obj.duration_ms,
                        tests_collected=run_obj.tests_collected,
                        tests_passed=run_obj.tests_passed,
                        tests_failed=run_obj.tests_failed,
                        tests_error=run_obj.tests_error,
                        tests_skipped=run_obj.tests_skipped,
                        all_pass=run_obj.all_passed,
                        results=[{
                            "nodeid": r.nodeid, "outcome": r.outcome,
                            "duration_sec": r.duration_sec, "longrepr": r.longrepr,
                        } for r in run_obj.results],
                        ac_mapping=test_verify.get("ac_results"),
                        summary_text=run_obj.summary_text,
                        stderr_tail=run_obj.stderr_tail,
                        error=run_obj.error,
                    )
                    db.add(tr)
                    db.flush()
                if not test_verify.get("all_pass", True):
                    gate_error = test_verify.get("error")
                    failing = [a for a in (test_verify.get("ac_results") or []) if not a.get("passed")]
                    if gate_error and not failing:
                        verification_issues.append(f"tests_gate: {gate_error}")
                    else:
                        verification_issues.append(
                            f"tests_failed: {len(failing)} AC(s) have failing/missing tests: "
                            + ", ".join(f"AC-{a['ac_index']}({a.get('tests_failed',0)}F/{a.get('tests_matched',0)})" for a in failing)
                        )

                # 3. KR measurement — for KRs linked to this task's objective with measurement_command
                kr_measurements: list[dict] = []
                if candidate.origin:
                    obj = db.query(Objective).filter(
                        Objective.project_id == proj.id,
                        Objective.external_id == candidate.origin,
                    ).first()
                    if obj:
                        krs_query = db.query(KeyResult).filter(
                            KeyResult.objective_id == obj.id,
                            KeyResult.measurement_command.isnot(None),
                        )
                        # Phase B: scope KR measurement to KRs this task claims to complete
                        if candidate.completes_kr_ids:
                            # e.g. ["KR0"] → map to positions 0
                            kr_positions = []
                            for kr_ref in candidate.completes_kr_ids:
                                try:
                                    kr_positions.append(int(kr_ref.replace("KR", "")))
                                except ValueError:
                                    pass
                            if kr_positions:
                                krs_query = krs_query.filter(KeyResult.position.in_(kr_positions))
                        krs = krs_query.all()
                        for kr in krs:
                            m = measure_kr(
                                workspace_dir=workspace,
                                kr_id=kr.id, kr_text=kr.text,
                                measurement_command=kr.measurement_command,
                                target_value=kr.target_value,
                                env_extra=infra_env or None,
                            )
                            kr_measurements.append({
                                "kr_id": kr.id, "kr_text": kr.text[:100],
                                "target_value": kr.target_value,
                                "measured_value": m.measured_value,
                                "target_hit": m.target_hit,
                                "return_code": m.return_code,
                                "error": m.error,
                                "stdout_tail": m.stdout_tail[-400:],
                            })
                            # Update KR state
                            if m.measured_value is not None:
                                kr.current_value = m.measured_value
                                if m.target_hit:
                                    commit_status_transition(kr, entity_type="key_result", target_state="ACHIEVED")
                                elif kr.status == "NOT_STARTED":
                                    commit_status_transition(kr, entity_type="key_result", target_state="IN_PROGRESS")

                            # P5.2 — silent-fail surfacing: when the measurement command
                            # crashed (timeout/rc!=0) OR ran cleanly but emitted no parseable
                            # number, leave a Finding so the user notices instead of seeing
                            # current_value=null forever.
                            failure_reason: str | None = None
                            if m.error:
                                failure_reason = (
                                    f"measurement command failed ({m.error})"
                                )
                            elif m.measured_value is None:
                                failure_reason = (
                                    "measurement command exited 0 but stdout contained "
                                    "no parseable number"
                                )
                            if failure_reason:
                                try:
                                    ext_id = _next_external_id(db, proj.id, Finding, "F")
                                    db.add(Finding(
                                        project_id=proj.id, execution_id=execution.id,
                                        external_id=ext_id,
                                        type="gap", severity="MEDIUM",
                                        title=f"KR measurement failed: KR-{kr.position} on {obj.external_id}",
                                        description=(
                                            f"{failure_reason}. KR text: {kr.text[:200]}. "
                                            f"Command: `{kr.measurement_command[:200]}`. "
                                            f"stderr tail: {(m.stderr_tail or '')[:300]}"
                                        ),
                                        suggested_action=(
                                            "Verify the measurement_command exists in the workspace "
                                            "(install missing tooling) and emits a numeric metric on stdout."
                                        ),
                                        evidence=(
                                            f"forge/kr_measurer rc={m.return_code} "
                                            f"measured={m.measured_value}"
                                        ),
                                    ))
                                    db.flush()
                                except Exception:
                                    db.rollback()
                verification_report["kr_measurements"] = kr_measurements

                # Decide accept/reject based on verification
                execution.validation_result = {
                    **(execution.validation_result or {}),
                    "verification": verification_report,
                    "verification_issues": verification_issues,
                }
                if verification_issues:
                    commit_status_transition(execution, entity_type="execution", target_state="REJECTED")
                    fix_hint = (
                        f"Verification failed (Forge-executed checks, not AI self-report): "
                        + "; ".join(verification_issues)
                        + ". Fix actual code/tests — declarations alone won't pass."
                    )
                    db.commit()
                    task_attempts[-1]["verification_failed"] = verification_issues
                    continue

                # All checks passed
                commit_status_transition(execution, entity_type="execution", target_state="ACCEPTED")
                execution.completed_at = dt.datetime.now(dt.timezone.utc)
                commit_status_transition(candidate, entity_type="task", target_state="DONE")
                candidate.completed_at = dt.datetime.now(dt.timezone.utc)
                db.commit()

                _update_run(db, run_id, current_phase="extract",
                            progress_message=f"{candidate.external_id}: extractor pulling decisions + findings")
                # ------ PHASE B: auto-extract decisions + findings from delivery ------
                try:
                    extraction = extract_from_delivery(
                        delivery=delivery,
                        invoke_fn=invoke_claude_with_key,
                        workspace_dir=workspace,
                        model=settings.claude_model,
                        max_budget_usd=1.0,
                        timeout_sec=300,
                    )
                except Exception as e:
                    db.rollback()
                    from app.services.delivery_extractor import ExtractionResult
                    extraction = ExtractionResult(error=f"extractor threw: {type(e).__name__}: {str(e)[:300]}")
                extracted_decisions_ext = []
                extracted_findings_ext = []
                if extraction.llm_call_meta:
                    # Log the extraction call
                    from app.services.claude_cli import CLIResult
                    # Record as purpose=extract (not executed, no standard _record_llm_call path)
                    llm_ext = LLMCall(
                        execution_id=execution.id, project_id=proj.id, purpose="extract",
                        model=settings.claude_model,
                        model_used=extraction.llm_call_meta.get("model_used"),
                        session_id=None,
                        prompt_hash="extract-" + (execution.prompt_hash or "")[:16],
                        prompt_chars=0, prompt_preview="(extraction prompt, see delivery_extractor.py)",
                        return_code=0,
                        is_error=bool(extraction.error),
                        parse_error=extraction.error,
                        duration_ms=extraction.llm_call_meta.get("duration_ms"),
                        cost_usd=extraction.llm_call_meta.get("cost_usd"),
                        response_text=None,
                        response_chars=0,
                        delivery_parsed={
                            "decisions": [{"issue":d.issue,"recommendation":d.recommendation,"reasoning":d.reasoning,"severity":d.severity} for d in extraction.decisions],
                            "findings": [{"type":f.type,"severity":f.severity,"title":f.title,"description":f.description,"file_path":f.file_path,"suggested_action":f.suggested_action} for f in extraction.findings],
                        },
                    )
                    db.add(llm_ext)
                    db.flush()
                    total_cost += extraction.llm_call_meta.get("cost_usd") or 0

                try:
                    for ed in extraction.decisions:
                        ext_id = _next_external_id(db, proj.id, Decision, "D")
                        d_row = Decision(
                            project_id=proj.id, execution_id=execution.id,
                            external_id=ext_id, task_id=candidate.id,
                            type=ed.type, issue=ed.issue,
                            recommendation=ed.recommendation, reasoning=ed.reasoning,
                            status="CLOSED", severity=ed.severity,
                        )
                        db.add(d_row)
                        db.flush()
                        extracted_decisions_ext.append(ext_id)
                        # CGAID artifact #5 — auto-export CLOSED ADR to in-repo .ai/decisions/
                        try:
                            from app.services.adr_exporter import export_decision
                            export_decision(
                                d_row, proj, settings.workspace_root,
                                task_ext_id=candidate.external_id,
                            )
                        except Exception:
                            pass  # filesystem export is best-effort; DB is source of truth

                    for ef in extraction.findings:
                        ext_id = _next_external_id(db, proj.id, Finding, "F")
                        f_row = Finding(
                            project_id=proj.id, execution_id=execution.id,
                            external_id=ext_id, type=ef.type, severity=ef.severity,
                            title=ef.title, description=ef.description,
                            file_path=ef.file_path, evidence="auto-extracted from delivery.reasoning",
                            suggested_action=ef.suggested_action,
                        )
                        db.add(f_row)
                        db.flush()
                        extracted_findings_ext.append(ext_id)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    # Extraction partial failure — task stays DONE, we lose the extracted items
                    # but log the error. Future improvement: per-row savepoint so valid items persist.
                    task_attempts[-1]["extraction_persist_error"] = f"{type(e).__name__}: {str(e)[:200]}"

                _update_run(db, run_id, current_phase="challenge",
                            progress_message=f"{candidate.external_id}: Opus challenging Sonnet's delivery")
                # ------ PHASE C: cross-model challenge (Opus challenges Sonnet) ------
                challenge_findings_ext = []
                challenge_verdict = None
                challenge_error = None
                try:
                    # P1.3 — resolve challenger_checks from the origin objective (and its
                    # dependency chain) so the Opus prompt actually honors user-configured checks.
                    from app.services.challenger import resolve_challenger_checks_for_task
                    extra_checks = resolve_challenger_checks_for_task(db, candidate)
                    chal = run_challenge(
                        task=candidate,
                        delivery=delivery,
                        acceptance_criteria=candidate.acceptance_criteria,
                        test_run_data=verification_report.get("tests"),
                        extracted_decisions=extraction.decisions,
                        extracted_findings=extraction.findings,
                        invoke_fn=invoke_claude_with_key,
                        workspace_dir=workspace,
                        model=settings.claude_model_challenger,
                        max_budget_usd=2.0,
                        timeout_sec=600,
                        extra_checks=extra_checks,
                    )
                except Exception as e:
                    db.rollback()
                    from app.services.challenger import ChallengeResult
                    chal = ChallengeResult(overall_verdict="ERROR", error=f"{type(e).__name__}: {str(e)[:200]}")

                # Persist challenge llm_call + findings
                try:
                    if chal.llm_call_meta:
                        llm_ch = LLMCall(
                            execution_id=execution.id, project_id=proj.id, purpose="challenge",
                            model=settings.claude_model_challenger,
                            model_used=chal.llm_call_meta.get("model_used"),
                            prompt_hash="challenge-" + (execution.prompt_hash or "")[:16],
                            prompt_chars=0, prompt_preview="(challenge prompt, see challenger.py)",
                            return_code=0,
                            is_error=bool(chal.error),
                            parse_error=chal.error,
                            duration_ms=chal.llm_call_meta.get("duration_ms"),
                            cost_usd=chal.llm_call_meta.get("cost_usd"),
                            response_chars=0,
                            delivery_parsed={
                                "overall_verdict": chal.overall_verdict,
                                "summary": chal.summary,
                                "per_claim_verdicts": chal.per_claim_verdicts,
                                "new_findings_count": len(chal.new_findings),
                                # P1.3 — audit trail for challenger_checks injection
                                "injected_checks_count": chal.llm_call_meta.get("injected_checks_count", 0),
                                "injected_checks": chal.llm_call_meta.get("injected_checks", []),
                            },
                        )
                        db.add(llm_ch)
                        db.flush()
                        total_cost += chal.llm_call_meta.get("cost_usd") or 0

                        # K4 auto-instrumentation: detect solo-verifier (challenger
                        # model == executor model) per ADR-012 distinct-actor.
                        # Idempotent per-execution; safe to call after every
                        # challenge LLMCall creation. Failures here MUST NOT
                        # break the pipeline — wrap in defensive try.
                        try:
                            from app.services.kill_criteria import detect_k4_solo_verifier
                            detect_k4_solo_verifier(db, execution.id)
                        except Exception:
                            # Logged-only audit; never raises into the executor path.
                            pass

                    for cf in chal.new_findings:
                        ext_id = _next_external_id(db, proj.id, Finding, "F")
                        db.add(Finding(
                            project_id=proj.id, execution_id=execution.id,
                            external_id=ext_id, type=cf.type, severity=cf.severity,
                            title=cf.title, description=cf.description,
                            file_path=cf.file_path,
                            evidence=f"challenger-surfaced ({settings.claude_model_challenger}); not found by Phase B extractor",
                            suggested_action=cf.suggested_action,
                        ))
                        db.flush()
                        challenge_findings_ext.append(ext_id)
                    challenge_verdict = chal.overall_verdict
                    challenge_error = chal.error
                    db.commit()
                except Exception as e:
                    db.rollback()
                    challenge_error = f"persist error: {type(e).__name__}: {str(e)[:200]}"

                task_attempts[-1]["verification"] = {
                    "tests_passed": verification_report.get("tests", {}).get("all_pass"),
                    "kr_measurements_count": len(kr_measurements),
                    "kr_hits": sum(1 for m in kr_measurements if m["target_hit"]),
                    "extracted_decisions": extracted_decisions_ext,
                    "extracted_findings": extracted_findings_ext,
                    "extraction_error": extraction.error,
                    "challenge_verdict": challenge_verdict,
                    "challenge_findings": challenge_findings_ext,
                    "challenge_claims_verified": chal.claims_verified,
                    "challenge_claims_refuted": chal.claims_refuted,
                    "challenge_error": challenge_error,
                }
                accepted = True
                break
            else:
                commit_status_transition(execution, entity_type="execution", target_state="REJECTED")
                fix_hint = val.fix_instructions
                db.commit()

        if not accepted:
            commit_status_transition(execution, entity_type="execution", target_state="FAILED")
            commit_status_transition(candidate, entity_type="task", target_state="FAILED")
            candidate.fail_reason = f"Max retries ({max_retries}) reached. Last fix_hint: {fix_hint[:300]}"
            db.commit()
            results.append({"task": candidate.external_id, "status": "FAILED", "attempts": task_attempts})
            _update_run(db, run_id,
                        tasks_failed=sum(1 for r in results if r["status"] == "FAILED"),
                        tasks_completed=sum(1 for r in results if r["status"] == "DONE"),
                        total_cost_usd=round(total_cost, 4),
                        progress_message=f"{candidate.external_id}: FAILED after {len(task_attempts)} attempts")
            try:
                from app.services.webhooks import dispatch_event as _dispatch
                if proj.organization_id:
                    _dispatch(db, proj.organization_id, "task.failed", {
                        "project": slug, "task": candidate.external_id,
                        "attempts": len(task_attempts),
                    })
            except Exception:
                pass  # webhook failure shouldn't crash orchestrate
            if body.stop_on_failure:
                break
            continue

        results.append({"task": candidate.external_id, "status": "DONE", "attempts": task_attempts})
        _update_run(db, run_id,
                    tasks_completed=sum(1 for r in results if r["status"] == "DONE"),
                    tasks_failed=sum(1 for r in results if r["status"] == "FAILED"),
                    total_cost_usd=round(total_cost, 4),
                    progress_message=f"{candidate.external_id}: DONE")
        try:
            from app.services.webhooks import dispatch_event as _dispatch
            if proj.organization_id:
                _dispatch(db, proj.organization_id, "task.done", {
                    "project": slug, "task": candidate.external_id,
                    "cost_usd": total_cost,
                })
        except Exception:
            pass

        # P1.2 — fire post-stage hooks (isolated try/except: a hook failure
        # MUST NOT abort the orchestrate loop).
        try:
            from app.services.hooks_runner import fire_hooks_for_task
            fire_hooks_for_task(
                db, proj, candidate,
                workspace_dir=workspace, api_key=anthropic_key_orchestrate,
            )
        except Exception:
            pass

    final = {
        "tasks_run": len(results),
        "results": results,
        "total_cost_usd": round(total_cost, 4),
        "workspace": workspace,
        "workspace_infra": infra_info,
    }
    # P5.6 — pick the right terminal status + non-misleading message.
    # "DONE" used to apply even when every task failed — the user got "Completed 1 tasks (0 done)".
    done_count = sum(1 for r in results if r["status"] == "DONE")
    failed_count = sum(1 for r in results if r["status"] == "FAILED")
    if failed_count == 0 and done_count > 0:
        final_status = "DONE"
        summary_msg = f"Completed {len(results)} task(s), all DONE."
    elif done_count > 0 and failed_count > 0:
        final_status = "PARTIAL_FAIL"
        summary_msg = f"Partial: {done_count} DONE, {failed_count} FAILED out of {len(results)}."
    elif done_count == 0 and failed_count > 0:
        final_status = "PARTIAL_FAIL"
        summary_msg = f"No tasks completed: {failed_count} FAILED out of {len(results)}."
    else:
        # No results at all (max_tasks=0 edge / loop bailed) — treat as DONE w/ zero work.
        final_status = "DONE"
        summary_msg = "Loop finished with no candidate tasks."
    _update_run(db, run_id, status=final_status, current_phase="done",
                progress_message=summary_msg,
                result=final, total_cost_usd=round(total_cost, 4),
                finished_at=dt.datetime.now(dt.timezone.utc))
    return final


# ---------- Async orchestrate (background) ----------

from fastapi import BackgroundTasks


@router.post("/projects/{slug}/orchestrate-async")
def orchestrate_async(
    slug: str,
    background_tasks: BackgroundTasks,
    body: OrchestrateRequest | None = None,
    db: Session = Depends(get_db),
):
    """Start orchestrate in background. Returns run_id immediately. Poll GET /orchestrate-runs/{id}."""
    proj = _project(db, slug)
    body = body or OrchestrateRequest()
    run = OrchestrateRun(
        project_id=proj.id,
        params=body.model_dump(),
        status="PENDING",
        progress_message="Queued",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(_run_orchestrate_background, slug, body.model_dump(), run.id)
    return {"run_id": run.id, "status": "PENDING", "poll_url": f"/api/v1/orchestrate-runs/{run.id}"}


@router.get("/orchestrate-runs/{run_id}")
def orchestrate_run_status(run_id: int, db: Session = Depends(get_db)):
    run = db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).first()
    if not run:
        raise HTTPException(404)
    elapsed_sec = None
    if run.started_at:
        end = run.finished_at or dt.datetime.now(dt.timezone.utc)
        elapsed_sec = int((end - run.started_at).total_seconds())
    return {
        "id": run.id, "project_id": run.project_id,
        "status": run.status, "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "elapsed_sec": elapsed_sec,
        "current_task_external_id": run.current_task_external_id,
        "current_phase": run.current_phase,
        "progress_message": run.progress_message,
        "tasks_completed": run.tasks_completed,
        "tasks_failed": run.tasks_failed,
        "total_cost_usd": run.total_cost_usd,
        "params": run.params,
        "error": run.error,
        "result": run.result,
        "cancel_requested": run.cancel_requested,
        "pause_requested": run.pause_requested,
        "paused_at": run.paused_at.isoformat() if run.paused_at else None,
        "resumed_at": run.resumed_at.isoformat() if run.resumed_at else None,
    }


@router.post("/orchestrate-runs/{run_id}/cancel")
def orchestrate_run_cancel(run_id: int, db: Session = Depends(get_db)):
    run = db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).first()
    if not run:
        raise HTTPException(404)
    if run.status in ("DONE", "FAILED", "CANCELLED", "BUDGET_EXCEEDED"):
        raise HTTPException(409, "Run already finished")
    run.cancel_requested = True
    db.commit()
    return {"cancel_requested": True, "status": run.status}


@router.post("/projects/{slug}/tasks/{external_id}/retry")
def task_retry(slug: str, external_id: str, db: Session = Depends(get_db)):
    """Reset a FAILED/DONE task back to TODO so it can be re-executed in the next orchestrate run.

    Does NOT revert git changes — user must decide whether to keep existing partial work.
    """
    proj = _project(db, slug)
    t = db.query(Task).filter(
        Task.project_id == proj.id,
        Task.external_id == external_id,
    ).first()
    if not t:
        raise HTTPException(404, f"Task {external_id} not found")
    if t.status not in ("FAILED", "DONE", "SKIPPED"):
        raise HTTPException(409, f"Task is {t.status}; only FAILED/DONE/SKIPPED can be retried")

    previous_status = t.status
    commit_status_transition(t, entity_type="task", target_state="TODO")
    t.started_at = None
    t.completed_at = None
    t.agent = None
    db.commit()
    return {
        "task": external_id,
        "previous_status": previous_status,
        "status": "TODO",
        "message": "Task reset — trigger Orchestrate to re-execute.",
    }


# ---------- /projects/{slug}/tasks/{ext}/report — trustworthy DONE report ----------

@router.get("/projects/{slug}/tasks/{external_id}/report")
def task_report(slug: str, external_id: str, db: Session = Depends(get_db)):
    """Trustworthy DONE report per task.

    Aggregates:
    - Requirements covered (task.requirement_refs → Knowledge lookup)
    - Objective + KRs this task maps to (origin + completes_kr_ids)
    - Files changed (from changes + git diff via TestRun.ac_mapping et al — currently from delivery only)
    - Tests executed (from test_runs — Forge-executed, not AI-declared)
    - AC mapping (scenario_type + pass/fail per test)
    - KR measurements (from verification_report)
    - Auto-extracted decisions + findings (purpose=extract llm_call)
    - Cost breakdown
    """
    proj = _project(db, slug)
    # If legacy collisions exist (pre-B1 plans), prefer the most recent task with this external_id
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id,
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404, f"Task {external_id} not found")

    # Latest ACCEPTED execution
    latest_exec = db.query(Execution).filter(
        Execution.task_id == task.id, Execution.status == "ACCEPTED",
    ).order_by(Execution.id.desc()).first()

    all_execs = db.query(Execution).filter(Execution.task_id == task.id).order_by(Execution.id).all()

    # Requirements
    req_refs = task.requirement_refs or []
    req_details = []
    known: dict = {}
    if req_refs:
        # Try to match against Knowledge external_id (e.g. "SRC-001")
        src_ids = {r.split()[0].split("§")[0].strip() for r in req_refs}
        known = {
            k.external_id: k for k in db.query(Knowledge).filter(
                Knowledge.project_id == proj.id,
                Knowledge.external_id.in_(src_ids),
            ).all()
        }
        for ref in req_refs:
            src_id = ref.split()[0].split("§")[0].strip()
            k = known.get(src_id)
            req_details.append({
                "ref": ref,
                "source_id": src_id,
                "source_title": k.title if k else None,
                "source_known": k is not None,
            })

    # Coverage-of-source-terms — retroactive-replay: catches pilot F2/F3
    # (terms mentioned in source docs but absent from all AC texts)
    coverage_report = None
    if known and task.acceptance_criteria:
        from app.services.coverage_analyzer import analyze_coverage
        source_texts = {
            src_id: k.content for src_id, k in known.items() if k.content
        }
        ac_texts = [ac.text for ac in task.acceptance_criteria if ac.text]
        if source_texts and ac_texts:
            coverage_report = analyze_coverage(source_texts, ac_texts, max_gap_terms=15)

    # Objective + KRs
    obj_info = None
    if task.origin:
        obj = db.query(Objective).filter(
            Objective.project_id == proj.id,
            Objective.external_id == task.origin,
        ).first()
        if obj:
            krs_all = db.query(KeyResult).filter(KeyResult.objective_id == obj.id).order_by(KeyResult.position).all()
            completes_positions = set()
            for kr_ref in (task.completes_kr_ids or []):
                try:
                    completes_positions.add(int(kr_ref.replace("KR", "")))
                except ValueError:
                    pass
            obj_info = {
                "external_id": obj.external_id,
                "title": obj.title,
                "status": obj.status,
                "key_results": [
                    {
                        "position": kr.position,
                        "text": kr.text,
                        "kr_type": kr.kr_type,
                        "target_value": kr.target_value,
                        "current_value": kr.current_value,
                        "status": kr.status,
                        "completed_by_this_task": kr.position in completes_positions,
                    }
                    for kr in krs_all
                ],
            }

    # Test runs for latest exec
    tests_data = None
    if latest_exec:
        tr = db.query(TestRun).filter(TestRun.execution_id == latest_exec.id).order_by(TestRun.id.desc()).first()
        if tr:
            tests_data = {
                "language": tr.language,
                "collected": tr.tests_collected,
                "passed": tr.tests_passed,
                "failed": tr.tests_failed,
                "error": tr.tests_error,
                "skipped": tr.tests_skipped,
                "all_pass": tr.all_pass,
                "duration_ms": tr.duration_ms,
                "per_test": tr.results or [],
                "per_ac": tr.ac_mapping or [],
            }

    # Verification report from latest exec
    verification = None
    diff_data = None
    if latest_exec and latest_exec.validation_result:
        verification = latest_exec.validation_result.get("verification")
        # Live git diff if we have head_before
        gd_meta = (verification or {}).get("git_diff") or {}
        head_before = gd_meta.get("head_before")
        head_after = gd_meta.get("head_after")
        if head_before and head_after:
            from app.services.workspace_browser import git_diff as _git_diff
            workspace = _workspace(slug)
            diff_data = _git_diff(workspace, head_before, head_after)
            # P2.3 — also compute split-view rows for the side-by-side toggle.
            if diff_data and isinstance(diff_data, dict) and diff_data.get("diff") and not diff_data.get("error"):
                try:
                    from app.services.diff_renderer import build_split_diff_rows
                    diff_data["split_rows"] = build_split_diff_rows(diff_data["diff"])
                except Exception:
                    diff_data["split_rows"] = []

    # Auto-extracted decisions + findings linked to task
    extracted_decisions = [
        {
            "external_id": d.external_id, "type": d.type,
            "issue": d.issue, "recommendation": d.recommendation,
            "reasoning": d.reasoning, "severity": d.severity,
        }
        for d in db.query(Decision).filter(Decision.task_id == task.id).all()
    ]
    all_task_findings = db.query(Finding).filter(
        Finding.execution_id.in_([e.id for e in all_execs])
    ).all()
    extracted_findings = [
        {
            "external_id": f.external_id, "type": f.type, "severity": f.severity,
            "title": f.title, "description": f.description,
            "file_path": f.file_path, "suggested_action": f.suggested_action,
            "status": f.status,
            "source": "challenger" if "challenger-surfaced" in (f.evidence or "") else "extractor",
        }
        for f in all_task_findings
    ]

    # Challenge summary from LLMCall purpose=challenge
    challenge_summary = None
    ch_call = db.query(LLMCall).filter(
        LLMCall.execution_id.in_([e.id for e in all_execs]),
        LLMCall.purpose == "challenge",
    ).order_by(LLMCall.id.desc()).first()
    if ch_call:
        challenge_summary = {
            "model_used": ch_call.model_used,
            "cost_usd": ch_call.cost_usd,
            "duration_ms": ch_call.duration_ms,
            "verdict": (ch_call.delivery_parsed or {}).get("overall_verdict"),
            "summary": (ch_call.delivery_parsed or {}).get("summary"),
            "claims_verified": sum(1 for c in (ch_call.delivery_parsed or {}).get("per_claim_verdicts",[]) if c.get("verified") is True),
            "claims_refuted": sum(1 for c in (ch_call.delivery_parsed or {}).get("per_claim_verdicts",[]) if c.get("verified") is False),
            "per_claim_verdicts": (ch_call.delivery_parsed or {}).get("per_claim_verdicts", []),
        }

    # Cost breakdown per exec
    cost_rows = db.query(LLMCall).filter(
        LLMCall.execution_id.in_([e.id for e in all_execs])
    ).all()
    total_cost = sum(c.cost_usd or 0 for c in cost_rows)
    cost_by_purpose = {}
    for c in cost_rows:
        cost_by_purpose.setdefault(c.purpose, 0)
        cost_by_purpose[c.purpose] += c.cost_usd or 0

    # AC not_executed flags from delivery
    not_executed = []
    if latest_exec and latest_exec.delivery:
        cc = latest_exec.delivery.get("completion_claims") or {}
        for ne in cc.get("not_executed", []):
            not_executed.append({"action": ne.get("action"), "reason": ne.get("reason"), "impact": ne.get("impact")})

    # P2.1 — surface origin_finding link so the task page can show a chip.
    origin_finding_info = None
    if getattr(task, "origin_finding_id", None):
        of = db.query(Finding).filter(Finding.id == task.origin_finding_id).first()
        if of:
            origin_finding_info = {
                "external_id": of.external_id,
                "title": of.title,
                "severity": of.severity,
                "status": of.status,
            }

    # P1.4 — expose Execution.mode so task_report.html can render the
    # direct|crafted|shadow|plan badge. Previously stored but never surfaced.
    latest_exec_info = None
    if latest_exec:
        started = getattr(latest_exec, "created_at", None)
        latest_exec_info = {
            "id": latest_exec.id,
            "status": latest_exec.status,
            "mode": latest_exec.mode or "direct",
            "crafter_call_id": latest_exec.crafter_call_id,
            "started_at": started.isoformat() if started else None,
            "completed_at": latest_exec.completed_at.isoformat() if latest_exec.completed_at else None,
        }

    return {
        "task": {
            "external_id": task.external_id, "name": task.name,
            "type": task.type, "status": task.status,
            "ceremony_level": task.ceremony_level,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "requirement_refs": task.requirement_refs,
            "completes_kr_ids": task.completes_kr_ids,
            "produces": task.produces,
        },
        "latest_execution": latest_exec_info,
        "origin_finding": origin_finding_info,
        "requirements_covered": req_details,
        "coverage": coverage_report,
        "objective": obj_info,
        "acceptance_criteria": [
            {
                "position": ac.position, "text": ac.text,
                "scenario_type": ac.scenario_type, "verification": ac.verification,
                "test_path": ac.test_path, "command": ac.command,
                "source_ref": ac.source_ref,  # B2 — surfaces "INVENTED BY LLM" badge
                "last_executed_at": ac.last_executed_at.isoformat() if ac.last_executed_at else None,
                "source_llm_call_id": ac.source_llm_call_id,  # B4 — "?" trace link
            }
            for ac in task.acceptance_criteria
        ],
        "tests_executed_by_forge": tests_data,
        "verification_report": verification,
        "auto_extracted_decisions": extracted_decisions,
        "auto_extracted_findings": extracted_findings,
        "challenge": challenge_summary,
        "diff": diff_data,
        "not_executed_claims": not_executed,
        "attempts": len(all_execs),
        "cost_usd": round(total_cost, 4),
        "cost_by_purpose": {k: round(v, 4) for k, v in cost_by_purpose.items()},
    }


# ---------- /projects/{slug}/llm-calls ----------

@router.get("/projects/{slug}/llm-calls")
def list_llm_calls(slug: str, limit: int = Query(50, le=500), db: Session = Depends(get_db)):
    proj = _project(db, slug)
    calls = db.query(LLMCall).filter(LLMCall.project_id == proj.id).order_by(LLMCall.id.desc()).limit(limit).all()
    return [
        {
            "id": c.id,
            "purpose": c.purpose,
            "execution_id": c.execution_id,
            "model_used": c.model_used,
            "cost_usd": c.cost_usd,
            "duration_ms": c.duration_ms,
            "input_tokens": c.input_tokens,
            "output_tokens": c.output_tokens,
            "is_error": c.is_error,
            "parse_error": c.parse_error,
            "response_chars": c.response_chars,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in calls
    ]


@router.get("/llm-calls/{call_id}")
def get_llm_call(call_id: int, db: Session = Depends(get_db)):
    c = db.query(LLMCall).filter(LLMCall.id == call_id).first()
    if not c:
        raise HTTPException(404)
    return {
        "id": c.id, "purpose": c.purpose, "execution_id": c.execution_id,
        "model": c.model, "model_used": c.model_used, "session_id": c.session_id,
        "prompt_chars": c.prompt_chars, "prompt_preview": c.prompt_preview,
        "full_prompt": c.full_prompt,
        "response_text": c.response_text,
        "delivery_parsed": c.delivery_parsed,
        "cost_usd": c.cost_usd, "duration_ms": c.duration_ms,
        "input_tokens": c.input_tokens, "output_tokens": c.output_tokens,
        "is_error": c.is_error, "parse_error": c.parse_error,
        "stderr_tail": c.stderr_tail,
        "workspace_dir": c.workspace_dir,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
