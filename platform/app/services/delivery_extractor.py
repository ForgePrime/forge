"""Second-pass LLM extraction of implementation decisions + out-of-scope findings.

After a task is ACCEPTED by primary validator + Phase A verification, this service:
1. Sends delivery.reasoning + delivery.changes + delivery.assumptions to a second
   Claude call with extraction prompt
2. Parses the JSON into {decisions: [...], findings: [...]}
3. Returns structured items for the orchestrator to persist as Decision/Finding rows

This surfaces "hidden decisions" (e.g. "used JWT with 15min TTL because...") and
"noticed but unfixed" findings that currently only live in delivery text.
"""

import json
from dataclasses import dataclass, field


@dataclass
class ExtractedDecision:
    issue: str             # what was decided
    recommendation: str    # the choice made
    reasoning: str         # why
    type: str = "implementation"
    severity: str = "LOW"


@dataclass
class ExtractedFinding:
    type: str              # bug | smell | opportunity | gap
    severity: str          # LOW | MEDIUM | HIGH
    title: str
    description: str
    file_path: str | None = None
    suggested_action: str | None = None


@dataclass
class ExtractionResult:
    decisions: list[ExtractedDecision] = field(default_factory=list)
    findings: list[ExtractedFinding] = field(default_factory=list)
    llm_call_meta: dict | None = None
    error: str | None = None


EXTRACT_PROMPT_TEMPLATE = """Jesteś analitykiem jakości dostaw od agenta AI.

Otrzymasz delivery (reasoning + changes + assumptions) od agenta który właśnie
zakończył task. Twoim zadaniem jest wyekstrahować DWIE rzeczy:

1. **DECISIONS** — każda KONKRETNA decyzja implementacyjna którą agent podjął a która:
   - NIE była wyraźnie wskazana w instrukcji taska
   - może mieć konsekwencje dla dalszych tasków / infrastruktury / bezpieczeństwa
   - jest niejawna (nie ma o niej osobnego rekordu w DB decisions)
   Przykłady: wybór biblioteki, architektury (pessimistic vs optimistic lock), algorytmu,
   konkretnej stałej (JWT TTL = 15min), sposobu obsługi błędów, poziomu izolacji transakcji.

2. **FINDINGS** — każda rzecz którą agent ZAUWAŻYŁ ale nie naprawił:
   - bug poza scope taska
   - code smell / tech debt
   - brak testu dla edge case
   - brak dokumentacji
   - niezgodność z dokumentem źródłowym
   - opportunity for improvement

Zasady:
- NIE duplikuj tego co już jest w delivery.assumptions[] (te są wyraźnie flagowane).
- Bądź selektywny. Lepiej 0 findings niż 10 trywialnych.
- Każda pozycja musi mieć KONKRETNE odniesienie (plik, funkcja, decyzja).

DELIVERY DO ANALIZY:

Reasoning:
{reasoning}

Changes:
{changes}

Assumptions:
{assumptions}

Impact analysis:
{impact}

Completion claims:
{completion_claims}

ODPOWIEDŹ — czysty JSON, bez markdown fence:

{{
  "decisions": [
    {{
      "issue": "krótki opis co zostało wybrane/ustalone (max 200 znaków)",
      "recommendation": "konkretna decyzja/wartość (np. 'JWT access TTL = 15 minutes')",
      "reasoning": "dlaczego (max 300 znaków)",
      "severity": "LOW|MEDIUM|HIGH"
    }}
  ],
  "findings": [
    {{
      "type": "bug|smell|opportunity|gap",
      "severity": "LOW|MEDIUM|HIGH",
      "title": "krótki tytuł",
      "description": "szczegóły (max 400 znaków)",
      "file_path": "opcjonalna ścieżka",
      "suggested_action": "opcjonalna sugestia fix"
    }}
  ]
}}

Jeśli nic wartościowego — zwróć {{"decisions": [], "findings": []}}.
"""


def extract_from_delivery(
    delivery: dict,
    invoke_fn,
    workspace_dir: str,
    model: str = "sonnet",
    max_budget_usd: float = 1.0,
    timeout_sec: int = 300,
) -> ExtractionResult:
    """Run extraction LLM call. invoke_fn must match signature of claude_cli.invoke_claude.

    Returns ExtractionResult with lists of ExtractedDecision / ExtractedFinding.
    """
    reasoning = (delivery.get("reasoning") or "").strip()
    if not reasoning or len(reasoning) < 50:
        return ExtractionResult(error="reasoning too short to extract")

    changes = delivery.get("changes") or []
    assumptions = delivery.get("assumptions") or []
    impact = delivery.get("impact_analysis") or {}
    completion = delivery.get("completion_claims") or {}

    prompt = EXTRACT_PROMPT_TEMPLATE.format(
        reasoning=reasoning[:4000],
        changes=json.dumps(changes, ensure_ascii=False, indent=2)[:3000],
        assumptions=json.dumps(assumptions, ensure_ascii=False, indent=2)[:2000],
        impact=json.dumps(impact, ensure_ascii=False, indent=2)[:2000],
        completion_claims=json.dumps(completion, ensure_ascii=False, indent=2)[:2000],
    )

    cli = invoke_fn(
        prompt=prompt,
        workspace_dir=workspace_dir,
        model=model,
        max_budget_usd=max_budget_usd,
        timeout_sec=timeout_sec,
    )

    result = ExtractionResult(llm_call_meta={
        "cost_usd": cli.cost_usd,
        "duration_ms": cli.duration_ms,
        "model_used": cli.model_used,
        "is_error": cli.is_error,
        "parse_error": cli.parse_error,
    })

    if cli.is_error or cli.parse_error:
        result.error = cli.parse_error or f"cli error: {cli.stderr[-500:] if cli.stderr else ''}"
        return result

    data = cli.delivery or {}
    if not isinstance(data, dict):
        result.error = "response not a JSON object"
        return result

    for d in data.get("decisions", []):
        if not isinstance(d, dict):
            continue
        issue = (d.get("issue") or "").strip()
        rec = (d.get("recommendation") or "").strip()
        if not issue or not rec:
            continue
        result.decisions.append(ExtractedDecision(
            issue=issue[:300],
            recommendation=rec[:500],
            reasoning=(d.get("reasoning") or "")[:500],
            severity=d.get("severity", "LOW").upper() if d.get("severity") else "LOW",
        ))

    for f in data.get("findings", []):
        if not isinstance(f, dict):
            continue
        title = (f.get("title") or "").strip()
        desc = (f.get("description") or "").strip()
        if not title:
            continue
        result.findings.append(ExtractedFinding(
            type=f.get("type", "opportunity"),
            severity=f.get("severity", "LOW").upper() if f.get("severity") else "LOW",
            title=title[:200],
            description=desc[:1000],
            file_path=f.get("file_path"),
            suggested_action=f.get("suggested_action"),
        ))

    return result
