"""Cross-model challenge service.

After a delivery is ACCEPTED by Sonnet (executor) + Phase A (mechanical tests)
+ Phase B (extraction), invoke Opus (challenger) to independently verify claims.

Opus is a different model — this breaks self-confirmation bias that would occur
if the same model evaluated its own output.

Challenger prompt:
- Receives delivery + AC + test results + reasoning
- Must answer VERIFIED or REFUTED for each claim with concrete evidence
- Returns structured JSON: {findings: [...], overall_verdict: "PASS|NEEDS_REWORK|FAIL"}

Findings with severity HIGH → create Finding rows, optionally flip task state to CHALLENGED.
"""

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


EXTRA_CHECKS_TEMPLATE = """

---

EXTRA CHALLENGER RULES — z objectives powiązanych z tym taskiem (P1.3).

To są rzeczy na które MUSISZ zwrócić uwagę dodatkowo. Dla każdego punktu, oceń
czy delivery przeszło sprawdzian. Jeśli coś nie jest możliwe do zweryfikowania
z samego delivery — napisz "NIE ZWERYFIKOWANE" w evidence (nie zgaduj PASS).

{checks_bullet_list}

---
"""


CHALLENGE_PROMPT_TEMPLATE = """Jesteś Challenger-Agent — niezależny weryfikator, inny model niż executor.

Właśnie zakończono task i oznaczono go jako DONE. Przed Tobą delivery agenta
oraz wyniki testów uruchomionych przez Forge. TWOIM ZADANIEM jest **niezależnie
zweryfikować** — NIE zaufać self-reportowi.

Zasady:
1. Dla każdego CLAIM sprawdź czy jest poparty konkretem (kod, test output, plik).
2. Szczególnie waż uwagę na:
   - Czy testy faktycznie testują to co mówi AC (nie tylko że PASS)?
   - Czy edge cases z dokumentów źródłowych są pokryte?
   - Czy decyzje implementacyjne NIE wprowadzają ukrytego długu / bugu?
   - Czy evidence odnosi się do KONKRETNEGO pliku / lini / assertion?
3. Jeśli NIE masz narzędzi do sprawdzenia czegoś — napisz "NIE ZWERYFIKOWANE"
   ZAMIAST domyślnie ufać.
4. NIE duplikuj findings z Phase B (jeśli coś już flagged — skup się na czymś nowym).

TASK INFO:

external_id: {task_ext}
name: {task_name}
type: {task_type}
requirement_refs: {req_refs}
completes_kr_ids: {kr_ids}

ACCEPTANCE CRITERIA:
{ac_block}

DELIVERY FROM EXECUTOR:
{delivery_block}

PHASE A TEST RESULTS (Forge-executed, not self-reported):
{test_block}

PHASE B AUTO-EXTRACTED:
{extraction_block}

---

ODPOWIEDŹ — czysty JSON bez markdown:

{{
  "per_claim_verdicts": [
    {{
      "claim": "co zostało zadeklarowane",
      "verified": true|false,
      "evidence": "konkretne: plik X linia Y, lub 'NIE ZWERYFIKOWANE' jeśli brak narzędzi"
    }}
  ],
  "new_findings": [
    {{
      "type": "bug|smell|opportunity|gap|risk",
      "severity": "HIGH|MEDIUM|LOW",
      "title": "krótki tytuł",
      "description": "szczegóły (max 400 znaków)",
      "file_path": "opcjonalna ścieżka",
      "suggested_action": "opcjonalna sugestia"
    }}
  ],
  "overall_verdict": "PASS|NEEDS_REWORK|FAIL",
  "summary": "1-2 zdania overall assessment"
}}

PASS = wszystkie claims verified, brak HIGH findings
NEEDS_REWORK = HIGH finding(s) ale core działa
FAIL = claims niespójne z kodem, task powinien wrócić do TODO
"""


def _normalize_check(raw) -> str | None:
    """Accept either a plain string or a dict with 'text'/'description' keys."""
    if raw is None:
        return None
    if isinstance(raw, str):
        txt = raw.strip()
        return txt or None
    if isinstance(raw, dict):
        txt = (raw.get("text") or raw.get("description") or raw.get("check") or "").strip()
        return txt or None
    return None


def resolve_challenger_checks_for_task(db: "Session", task) -> list[str]:
    """P1.3 — walk task.origin → Objective → dependency ancestors,
    collect all challenger_checks in order, dedupe by text.

    Returns [] when task has no origin or no objective matches.
    Never raises — a missing objective simply yields no checks.
    """
    if not getattr(task, "origin", None):
        return []
    from app.models import Objective  # local import — avoids circular

    root = db.query(Objective).filter(
        Objective.project_id == task.project_id,
        Objective.external_id == task.origin,
    ).first()
    if not root:
        return []

    # BFS through dependencies. Guard against cycles (shouldn't exist per
    # objective_dependencies cycle-check, but defensive).
    visited_ids: set[int] = set()
    order: list[str] = []
    seen_text: set[str] = set()
    queue = [root]
    while queue:
        obj = queue.pop(0)
        if obj.id in visited_ids:
            continue
        visited_ids.add(obj.id)
        for raw in (obj.challenger_checks or []):
            txt = _normalize_check(raw)
            if txt and txt not in seen_text:
                seen_text.add(txt)
                order.append(txt)
        for dep in (obj.dependencies or []):
            if dep.id not in visited_ids:
                queue.append(dep)
    return order


@dataclass
class ChallengeFinding:
    type: str
    severity: str
    title: str
    description: str
    file_path: str | None = None
    suggested_action: str | None = None


@dataclass
class ChallengeResult:
    overall_verdict: str = "PASS"  # PASS | NEEDS_REWORK | FAIL | ERROR
    summary: str = ""
    per_claim_verdicts: list[dict] = field(default_factory=list)
    new_findings: list[ChallengeFinding] = field(default_factory=list)
    claims_verified: int = 0
    claims_refuted: int = 0
    llm_call_meta: dict | None = None
    error: str | None = None


def run_challenge(
    task,
    delivery: dict,
    acceptance_criteria: list,
    test_run_data: dict | None,
    extracted_decisions: list,
    extracted_findings: list,
    invoke_fn,
    workspace_dir: str,
    model: str = "opus",
    max_budget_usd: float = 2.0,
    timeout_sec: int = 600,
    extra_checks: list[str] | None = None,
) -> ChallengeResult:
    """Invoke Opus (or whatever model is set) to independently verify the delivery.

    task: ORM Task object (has external_id, name, type, requirement_refs, completes_kr_ids)
    delivery: delivery dict from executor
    acceptance_criteria: list of AC ORM objects
    test_run_data: optional dict with tests_collected/passed/failed/ac_mapping
    extracted_decisions: list of ExtractedDecision
    extracted_findings: list of ExtractedFinding
    """
    ac_lines = []
    for ac in acceptance_criteria:
        pos = getattr(ac, "position", "?")
        text = getattr(ac, "text", "")
        stype = getattr(ac, "scenario_type", "")
        verif = getattr(ac, "verification", "")
        tp = getattr(ac, "test_path", "") or ""
        ac_lines.append(f"  AC-{pos} [{stype}] [{verif}] {text} → {tp}")
    ac_block = "\n".join(ac_lines) if ac_lines else "(none)"

    delivery_lines = []
    if delivery.get("reasoning"):
        delivery_lines.append(f"reasoning: {delivery['reasoning'][:1500]}")
    if delivery.get("changes"):
        changes_compact = [{"file": c.get("file_path"), "action": c.get("action"), "summary": c.get("summary", "")[:120]} for c in delivery["changes"]]
        delivery_lines.append(f"changes: {json.dumps(changes_compact, ensure_ascii=False)[:1500]}")
    if delivery.get("ac_evidence"):
        delivery_lines.append(f"ac_evidence: {json.dumps(delivery['ac_evidence'], ensure_ascii=False)[:1500]}")
    if delivery.get("assumptions"):
        delivery_lines.append(f"assumptions: {json.dumps(delivery['assumptions'], ensure_ascii=False)[:800]}")
    if delivery.get("impact_analysis"):
        delivery_lines.append(f"impact_analysis: {json.dumps(delivery['impact_analysis'], ensure_ascii=False)[:800]}")
    if delivery.get("completion_claims"):
        delivery_lines.append(f"completion_claims: {json.dumps(delivery['completion_claims'], ensure_ascii=False)[:800]}")
    delivery_block = "\n".join(delivery_lines)

    if test_run_data:
        tb = (
            f"language: {test_run_data.get('language')}\n"
            f"collected: {test_run_data.get('collected')} passed: {test_run_data.get('passed')} "
            f"failed: {test_run_data.get('failed')} error: {test_run_data.get('error')}\n"
        )
        per_ac = test_run_data.get('per_ac', [])
        if per_ac:
            tb += "per_ac:\n"
            for ac in per_ac:
                tb += f"  AC-{ac.get('ac_index')}: {'PASS' if ac.get('passed') else 'FAIL'} matched={ac.get('tests_matched')} path={ac.get('test_path')}\n"
        per_test = test_run_data.get('per_test', [])
        if per_test:
            tb += "per_test:\n"
            for t in per_test[:10]:
                tb += f"  {t.get('outcome')} {t.get('nodeid')} ({t.get('duration_sec',0):.2f}s)\n"
        test_block = tb
    else:
        test_block = "(no Phase A test run data available)"

    extraction_lines = []
    if extracted_decisions:
        extraction_lines.append("Decisions found by extractor:")
        for d in extracted_decisions[:8]:
            issue = d.issue if hasattr(d, "issue") else d.get("issue", "")
            rec = d.recommendation if hasattr(d, "recommendation") else d.get("recommendation", "")
            extraction_lines.append(f"  - {issue[:100]} → {rec[:80]}")
    if extracted_findings:
        extraction_lines.append("Findings found by extractor:")
        for f in extracted_findings[:8]:
            title = f.title if hasattr(f, "title") else f.get("title", "")
            sev = f.severity if hasattr(f, "severity") else f.get("severity", "")
            extraction_lines.append(f"  - [{sev}] {title[:120]}")
    extraction_block = "\n".join(extraction_lines) if extraction_lines else "(none)"

    prompt = CHALLENGE_PROMPT_TEMPLATE.format(
        task_ext=task.external_id,
        task_name=task.name,
        task_type=task.type,
        req_refs=task.requirement_refs or [],
        kr_ids=task.completes_kr_ids or [],
        ac_block=ac_block,
        delivery_block=delivery_block,
        test_block=test_block,
        extraction_block=extraction_block,
    )

    # P1.3 — splice objective-level challenger checks in right after the task header.
    # Placement: inject after the EXTRACTION block so the model has the context first
    # and then reads the "you must also verify these" rules just before the JSON contract.
    injected_checks: list[str] = []
    if extra_checks:
        injected_checks = [c for c in extra_checks if c and str(c).strip()]
    if injected_checks:
        bullets = "\n".join(f"- {c}" for c in injected_checks)
        extra_section = EXTRA_CHECKS_TEMPLATE.format(checks_bullet_list=bullets)
        # Insert just before the JSON contract marker ("ODPOWIEDŹ — czysty JSON...")
        marker = "ODPOWIEDŹ — czysty JSON bez markdown:"
        if marker in prompt:
            prompt = prompt.replace(marker, extra_section.strip() + "\n\n" + marker)
        else:
            prompt = prompt + extra_section

    cli = invoke_fn(
        prompt=prompt,
        workspace_dir=workspace_dir,
        model=model,
        max_budget_usd=max_budget_usd,
        timeout_sec=timeout_sec,
    )

    result = ChallengeResult(llm_call_meta={
        "cost_usd": cli.cost_usd,
        "duration_ms": cli.duration_ms,
        "model_used": cli.model_used,
        "is_error": cli.is_error,
        "parse_error": cli.parse_error,
        "injected_checks_count": len(injected_checks),
        "injected_checks": injected_checks,
    })

    if cli.is_error or cli.parse_error:
        result.error = cli.parse_error or f"cli error"
        result.overall_verdict = "ERROR"
        return result

    data = cli.delivery or {}
    if not isinstance(data, dict):
        result.error = "response not JSON object"
        result.overall_verdict = "ERROR"
        return result

    result.overall_verdict = data.get("overall_verdict", "PASS").upper()
    if result.overall_verdict not in ("PASS", "NEEDS_REWORK", "FAIL"):
        result.overall_verdict = "ERROR"
    result.summary = (data.get("summary") or "")[:500]
    result.per_claim_verdicts = data.get("per_claim_verdicts") or []
    result.claims_verified = sum(1 for c in result.per_claim_verdicts if c.get("verified") is True)
    result.claims_refuted = sum(1 for c in result.per_claim_verdicts if c.get("verified") is False)

    for f in data.get("new_findings", []):
        if not isinstance(f, dict):
            continue
        title = (f.get("title") or "").strip()
        desc = (f.get("description") or "").strip()
        if not title:
            continue
        result.new_findings.append(ChallengeFinding(
            type=f.get("type", "opportunity"),
            severity=(f.get("severity") or "LOW").upper(),
            title=title[:200],
            description=desc[:1000],
            file_path=f.get("file_path"),
            suggested_action=f.get("suggested_action"),
        ))

    return result
