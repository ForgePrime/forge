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

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    Project, Task, AcceptanceCriterion, Knowledge, Objective, KeyResult,
    Decision, Execution, LLMCall,
)
from app.services.claude_cli import invoke_claude, CLIResult
from app.services.prompt_parser import assemble_prompt
from app.services.contract_validator import validate_delivery, CheckResult
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["pipeline"])


# ---------- Helpers ----------

def _project(db: Session, slug: str) -> Project:
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404, f"Project '{slug}' not found")
    return proj


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
    files: list[UploadFile] = File(...),
    category: str = Form("source-document"),
    db: Session = Depends(get_db),
):
    """Upload source documents (SOW, stakeholder emails, glossaries, NFR).

    Each file saved as Knowledge row with category=source-document (default).
    Returns list of created Knowledge external_ids.
    """
    proj = _project(db, slug)
    created = []
    for f in files:
        raw = await f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("utf-8", errors="replace")

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
        )
        db.add(k)
        db.flush()
        created.append({"id": k.id, "external_id": ext_id, "filename": f.filename, "chars": len(content)})
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
    workspace = _workspace(slug)

    cli = invoke_claude(
        prompt=prompt,
        workspace_dir=workspace,
        model=settings.claude_model,
        max_budget_usd=settings.claude_budget_per_task_usd,
        timeout_sec=settings.claude_timeout_sec,
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
    workspace = _workspace(slug)

    cli = invoke_claude(
        prompt=prompt,
        workspace_dir=workspace,
        model=settings.claude_model,
        max_budget_usd=settings.claude_budget_per_task_usd,
        timeout_sec=settings.claude_timeout_sec,
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

    # Create tasks
    ext_id_to_task: dict[str, Task] = {}
    created = []
    for t_data in tasks_data:
        t = Task(
            project_id=proj.id,
            external_id=t_data.get("external_id") or _next_external_id(db, proj.id, Task, "T"),
            name=t_data.get("name", "untitled"),
            instruction=t_data.get("instruction"),
            type=t_data.get("type", "feature"),
            scopes=t_data.get("scopes", []),
            origin=t_data.get("origin", obj.external_id),
            produces=t_data.get("produces"),
        )
        db.add(t)
        db.flush()
        ext_id_to_task[t.external_id] = t
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

    # Resolve dependencies
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


@router.post("/projects/{slug}/orchestrate")
def orchestrate(slug: str, body: OrchestrateRequest | None = None, db: Session = Depends(get_db)):
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

        # Claim
        candidate.status = "IN_PROGRESS"
        candidate.agent = "orchestrator-cli"
        candidate.started_at = dt.datetime.now(dt.timezone.utc)
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

        # Retry loop
        task_attempts = []
        accepted = False
        fix_hint = ""
        for attempt in range(1, max_retries + 1):
            full_prompt = asm.prompt_text + EXECUTE_SUFFIX
            if fix_hint:
                full_prompt += (
                    f"\n\n---\n\nPOPRZEDNIA PRÓBA BYŁA ODRZUCONA.\n"
                    f"Co trzeba naprawić: {fix_hint}\n\n"
                    f"WAŻNE: odpowiedź MUSI być JSON w formacie wyżej. "
                    f"Jeśli nie możesz czegoś wykonać, wpisz to w `completion_claims.not_executed` "
                    f"ZAMIAST pisać instrukcje w tekście.\n"
                )

            cli = invoke_claude(
                prompt=full_prompt,
                workspace_dir=workspace,
                model=settings.claude_model,
                max_budget_usd=settings.claude_budget_per_task_usd,
                timeout_sec=settings.claude_timeout_sec,
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
            val = validate_delivery(delivery, contract_def, candidate.type, None)
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
                execution.status = "ACCEPTED"
                execution.completed_at = dt.datetime.now(dt.timezone.utc)
                candidate.status = "DONE"
                candidate.completed_at = dt.datetime.now(dt.timezone.utc)
                db.commit()
                accepted = True
                break
            else:
                execution.status = "REJECTED"
                fix_hint = val.fix_instructions
                db.commit()

        if not accepted:
            execution.status = "FAILED"
            candidate.status = "FAILED"
            candidate.fail_reason = f"Max retries ({max_retries}) reached. Last fix_hint: {fix_hint[:300]}"
            db.commit()
            results.append({"task": candidate.external_id, "status": "FAILED", "attempts": task_attempts})
            if body.stop_on_failure:
                break
            continue

        results.append({"task": candidate.external_id, "status": "DONE", "attempts": task_attempts})

    return {
        "tasks_run": len(results),
        "results": results,
        "total_cost_usd": round(total_cost, 4),
        "workspace": workspace,
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
