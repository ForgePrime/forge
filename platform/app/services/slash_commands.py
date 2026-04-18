"""Slash-command handlers — deterministic helpers the AI sidebar can call directly.

User types `/find-ambiguity` or `/cost-drill @T-005`. The chat endpoint can
detect the slash prefix and route to a handler here. Handlers return a dict
compatible with ai_chat.ChatResult (answer, not_checked, tool_calls, ...).

Design: handlers do NOT invoke the LLM — they're cheap, deterministic, auditable.
Expensive LLM-backed operations should be a separate class of skill.
"""
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Decision, Finding, Knowledge, Objective, Project, Task, AcceptanceCriterion,
    LLMCall, Execution, ExecutionAttempt,
)


@dataclass
class SlashResult:
    answer: str
    not_checked: list[str] = field(default_factory=list)
    tool_calls: list = field(default_factory=list)


def _parse_mentions(text: str) -> list[str]:
    return re.findall(r"@([A-Za-z]+-\d+)", text)


# -------------------- handlers --------------------

def cmd_find_ambiguity(db: Session, project: Project | None, args: str) -> SlashResult:
    if not project:
        return SlashResult(
            answer="This command requires a project context. Open a project page first.",
            not_checked=["No scan performed."],
        )
    opens = db.query(Decision).filter(
        Decision.project_id == project.id, Decision.status == "OPEN"
    ).all()
    if not opens:
        return SlashResult(
            answer=f"No OPEN decisions (ambiguities) found in project {project.slug}.\n"
                   "This does not mean the project is ambiguity-free — only that no analysis task flagged any OPEN decision.",
            not_checked=[
                "Did not re-scan KB for newly introduced conflicts.",
                "Did not check if resolved decisions remain consistent with current KB state.",
            ],
        )
    lines = [f"Found {len(opens)} OPEN decision(s) in {project.slug}:"]
    for d in opens:
        lines.append(f"- {d.external_id} [{d.severity or 'n/a'}] {d.issue or d.type}")
        if d.recommendation:
            lines.append(f"    rec: {d.recommendation[:200]}")
    return SlashResult(
        answer="\n".join(lines),
        not_checked=[
            "Only showed status=OPEN decisions from the decisions table; other ambiguity signals "
            "(e.g. unsourced AC) are not checked by this command.",
            "Did not evaluate severity ordering — list is DB-order, not priority-order.",
        ],
    )


def cmd_generate_scenarios(db: Session, project: Project | None, args: str) -> SlashResult:
    if not project:
        return SlashResult(
            answer="Open a project or objective page first.",
            not_checked=["Nothing scanned."],
        )
    mentions = _parse_mentions(args)
    obj_ids = [m for m in mentions if m.upper().startswith("O-")]
    if not obj_ids:
        return SlashResult(
            answer="Provide one or more objectives. Example: /generate-scenarios @O-001 @O-002",
            not_checked=["No objective identified."],
        )
    # This is a stub — real version would invoke a SKILL via LLM. For now, return
    # deterministic template scenarios so the UX contract is enforceable.
    tpl = [
        "Input arrives in an unexpected encoding (UTF-16, CP1250 with BOM).",
        "Two concurrent writers race on the same row; no lock.",
        "External dependency timeout mid-operation; partial commit left.",
        "User with revoked permissions still holds a valid session token.",
        "Storage backend returns 500 on a supposedly-idempotent retry.",
    ]
    lines = [f"(stub) Non-happy-path scenarios for {', '.join(obj_ids)}:"]
    for i, s in enumerate(tpl, 1):
        lines.append(f"{i}. {s}")
    return SlashResult(
        answer="\n".join(lines),
        not_checked=[
            "These scenarios are a generic template — not derived from the objective's actual AC or KB.",
            "Real scenario generation should use the `SK-scenario-gen-nonhappy` skill (LLM).",
        ],
    )


def cmd_reverse_trace(db: Session, project: Project | None, args: str) -> SlashResult:
    mentions = _parse_mentions(args)
    if not mentions or not project:
        return SlashResult(
            answer="Usage: /reverse-trace @T-005 (from a project page)",
            not_checked=["No mention parsed."],
        )
    target = mentions[0]
    # Try matching as task first
    if target.upper().startswith("T-"):
        t = db.query(Task).filter(
            Task.project_id == project.id, Task.external_id == target
        ).order_by(Task.id.desc()).first()
        if not t:
            return SlashResult(
                answer=f"Task {target} not found in {project.slug}.",
                not_checked=["No entity to trace."],
            )
        chain = [f"Task {t.external_id}: {t.name}"]
        if t.origin:
            obj = db.query(Objective).filter(
                Objective.project_id == project.id,
                Objective.external_id == t.origin,
            ).first()
            if obj:
                chain.append(f"  ← origin objective {obj.external_id}: {obj.title}")
        if t.requirement_refs:
            for ref in (t.requirement_refs or []):
                chain.append(f"  ← requirement ref: {ref}")
        if t.completes_kr_ids:
            for kr in t.completes_kr_ids:
                chain.append(f"  ← satisfies KR: {kr}")
        return SlashResult(
            answer="Reverse trace:\n" + "\n".join(chain),
            not_checked=[
                "Did not inspect actual git diff to find which code files / lines implement this task.",
                "Did not cross-reference with related Decision records.",
                "Only one-hop trace shown (task → origin objective); multi-hop chain not traversed.",
            ],
        )
    return SlashResult(
        answer=f"Reverse trace for {target} not implemented yet — only T-* tasks are supported in v1.",
        not_checked=["No operation performed."],
    )


def cmd_cost_drill(db: Session, project: Project | None, args: str) -> SlashResult:
    mentions = _parse_mentions(args)
    if not mentions or not project:
        return SlashResult(
            answer="Usage: /cost-drill @T-005",
            not_checked=["No task mention parsed."],
        )
    ext = mentions[0]
    t = db.query(Task).filter(
        Task.project_id == project.id, Task.external_id == ext
    ).order_by(Task.id.desc()).first()
    if not t:
        return SlashResult(
            answer=f"Task {ext} not found.",
            not_checked=["Nothing to drill into."],
        )
    execs = db.query(Execution).filter(Execution.task_id == t.id).all()
    if not execs:
        return SlashResult(
            answer=f"Task {ext} has no executions recorded.",
            not_checked=["Nothing to analyze."],
        )
    calls = db.query(LLMCall).filter(
        LLMCall.execution_id.in_([e.id for e in execs])
    ).all()
    by_purpose: dict[str, float] = {}
    for c in calls:
        by_purpose[c.purpose] = by_purpose.get(c.purpose, 0) + (c.cost_usd or 0)
    total = sum(by_purpose.values())
    lines = [f"Cost breakdown for {ext} (${total:.4f} total over {len(calls)} LLM calls):"]
    for p, v in sorted(by_purpose.items(), key=lambda kv: -kv[1]):
        pct = 100 * v / total if total else 0
        lines.append(f"  {p}: ${v:.4f} ({pct:.0f}%)")
    # Retries
    retries = db.query(ExecutionAttempt).filter(
        ExecutionAttempt.execution_id.in_([e.id for e in execs])
    ).count()
    lines.append(f"\nExecution attempts: {retries}")
    return SlashResult(
        answer="\n".join(lines),
        not_checked=[
            "Did not analyze growth of context size across retries (would need per-call input_tokens trend).",
            "Did not compare against other tasks' cost distribution in this project.",
        ],
    )


def cmd_list_not_executed(db: Session, project: Project | None, args: str) -> SlashResult:
    if not project:
        return SlashResult(answer="Open a project page first.", not_checked=["Nothing scanned."])
    tasks = db.query(Task).filter(Task.project_id == project.id).all()
    rows: list[str] = []
    for t in tasks:
        for ac in t.acceptance_criteria:
            verif = ac.verification or "manual"
            if verif == "manual":
                rows.append(f"  {t.external_id} · AC-{ac.position} · {ac.text[:80]} · MANUAL (no test)")
    if not rows:
        return SlashResult(
            answer="No manual-verification AC found — every AC has a test or command declared.",
            not_checked=[
                "Did not verify whether declared tests actually exist in the workspace.",
                "Did not check whether non-manual ACs have been executed recently.",
            ],
        )
    return SlashResult(
        answer=f"Manual-verification AC (not automatically executed) — {len(rows)} found:\n"
               + "\n".join(rows[:30]) + (f"\n… and {len(rows)-30} more" if len(rows) > 30 else ""),
        not_checked=[
            "Only manual-flagged AC were listed. AC with 'command' verification still require running the command; "
            "this command does not re-run them.",
        ],
    )


def cmd_help(db, project, args) -> SlashResult:
    return SlashResult(
        answer=(
            "Slash commands:\n"
            "  /find-ambiguity — list OPEN decisions in current project\n"
            "  /generate-scenarios @O-NNN — produce non-happy-path scenarios (stub)\n"
            "  /reverse-trace @T-NNN — trace task back to objective / KR / reqs\n"
            "  /cost-drill @T-NNN — cost breakdown per LLM purpose + retry count\n"
            "  /list-not-executed — AC that require manual verification\n"
            "  /help — this message\n"
        ),
        not_checked=[
            "This list may drift from actual routable commands — check slash_commands.ROUTE.",
        ],
    )


ROUTE: dict[str, callable] = {
    "/find-ambiguity": cmd_find_ambiguity,
    "/generate-scenarios": cmd_generate_scenarios,
    "/reverse-trace": cmd_reverse_trace,
    "/cost-drill": cmd_cost_drill,
    "/list-not-executed": cmd_list_not_executed,
    "/help": cmd_help,
}


def try_handle(db: Session, project: Project | None, message: str) -> SlashResult | None:
    if not message.startswith("/"):
        return None
    cmd, _, rest = message.partition(" ")
    cmd = cmd.lower()
    handler = ROUTE.get(cmd)
    if not handler:
        return SlashResult(
            answer=f"Unknown slash command `{cmd}`. Type /help for list.",
            not_checked=["No command dispatched."],
        )
    try:
        return handler(db, project, rest)
    except Exception as e:
        return SlashResult(
            answer=f"Internal error in slash handler: {type(e).__name__}",
            not_checked=[f"Handler raised: {e}", "No data safely returned."],
        )
