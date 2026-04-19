"""AI sidebar chat service — wraps invoke_claude with context injection + scope-limit enforcement.

Contract (skeptical UX):
- Every response MUST end with a "NOT_CHECKED:" section listing scope limits.
- Parser detects it, structures it into `not_checked` field.
- If absent after first call, return as-is with a UI warning (client renders amber "scope-limit missing").
"""
import json
import re
import time
import shutil
import subprocess
from dataclasses import dataclass

from app.services.claude_cli import invoke_claude, CLIResult


SYSTEM_TEMPLATE = """You are the AI sidebar of **Forge platform** (a FastAPI + PostgreSQL web app — NOT the original forge-cli that used tracker.json files).

## Architecture you MUST assume — overrides any prior knowledge of "Forge"
- **Backend**: FastAPI, SQLAlchemy 2.0, PostgreSQL.
- **Storage**: every entity (Project, Objective, KeyResult, Task, AcceptanceCriterion, Knowledge, Decision, Finding, OrchestrateRun, LLMCall, TestRun, Execution, ExecutionAttempt, Comment, Webhook, ShareLink, AIInteraction, Organization, Membership, User) is a row in PostgreSQL accessed via SQLAlchemy ORM. **No tracker.json. No filesystem state. No JSON file per project.**
- **API surface**: REST under `/api/v1/*` (JSON) and `/ui/*` (HTML). The `available_actions` block below lists exactly what is callable from the current page.
- **Auth**: cookie session `forge_token` (JWT) + double-submit CSRF cookie `forge_csrf` (header `X-CSRF-Token`). Per-org isolation is enforced.
- **Workspaces**: per-project work happens in `forge_output/{{project_slug}}/workspace` (a git repo for diff tracking). This is the workspace dir, not the data dir.
- **Pipeline**: ingest (upload Knowledge rows category=source-document) → analyze (LLM extracts objectives + decisions) → plan (LLM decomposes objectives into tasks) → orchestrate (LLM executes tasks Phase A test runner / Phase B findings extractor / Phase C cross-model challenger).
- If the user asks about a project's status, **infer from the visible_data and recent_activity provided below — do NOT invent file paths or tracker.json existence**.

## Skeptical contract — NOT OPTIONAL
You help the user scrutinise work. You do NOT build confidence for quick approval.
Every answer ends with a section literally named "NOT_CHECKED:" listing what you
could NOT verify or what was out of scope. Examples:
"I did not query findings table", "I did not read code in app/api/users.py",
"I did not check whether the listed actions actually succeed for the user's role".
Minimum 2 bullets in NOT_CHECKED, even on trivial answers.

## Tone
Direct. No apologies. Use the data in the page context. Cite entity IDs (e.g. T-005, O-002, SRC-001) where relevant.

## Current project context (from PostgreSQL via SQLAlchemy)
{project_context}

## Current page context (what the user is looking at)
Page: {page_title} ({page_id})
Route: {route}
Entity: {entity_type}:{entity_id}
Visible data (live JSON snapshot of what the page is rendering RIGHT NOW):
{visible_data_json}

## Available actions on this page (the technical contract — you can recommend these to the user)
{available_actions}

## Recent AI sidebar activity on this project
{recent_activity}

{plan_first_directive}

## User message
"""

PLAN_FIRST_DIRECTIVE = """
## PLAN-FIRST MODE (user opted in)
Before taking any action or giving a full answer, first return a short plan (3-5 bullet steps)
of what you WOULD do. Do not execute yet. Close with NOT_CHECKED:.
"""


@dataclass
class ChatResult:
    answer: str
    tool_calls: list
    not_checked: list[str]
    cost_usd: float
    duration_ms: int
    input_tokens: int | None
    output_tokens: int | None
    model_used: str | None
    system_prompt: str
    error_kind: str | None = None
    error_detail: str | None = None


def _format_actions(actions: list) -> str:
    if not actions:
        return "(no actions declared)"
    lines = []
    for a in actions:
        avail = "✓" if a.get("available", True) else "✗"
        line = f"  [{avail}] {a['label']} — {a['method']} {a['endpoint']}"
        if a.get("unavailable_reason"):
            line += f" (unavailable: {a['unavailable_reason']})"
        lines.append(line)
    return "\n".join(lines)


def _claude_cli_available() -> bool:
    return shutil.which("claude") is not None


def _extract_not_checked(text: str) -> tuple[str, list[str]]:
    """Split 'answer\nNOT_CHECKED:\n- ...\n- ...' into (answer, list).

    Returns ([original answer without the section], [bullets]).
    If the section is missing, returns (text, []).
    """
    m = re.search(r"\n+NOT_CHECKED:\s*\n(.*?)\s*\Z", text, re.DOTALL | re.IGNORECASE)
    if not m:
        return text.strip(), []
    bullets_raw = m.group(1)
    answer = text[: m.start()].strip()
    bullets = []
    for line in bullets_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # strip leading "- ", "* ", "• ", digits etc.
        line = re.sub(r"^[-*•\d.)]\s*", "", line).strip()
        if line:
            bullets.append(line)
    return answer, bullets


def build_system_prompt(*, page_ctx: dict, project_summary: str, recent_activity: str,
                        plan_first: bool) -> str:
    return SYSTEM_TEMPLATE.format(
        project_context=project_summary or "(no project context — user is on an org-wide page)",
        page_title=page_ctx.get("title", "?"),
        page_id=page_ctx.get("page_id", "unknown"),
        route=page_ctx.get("route", ""),
        entity_type=page_ctx.get("entity_type") or "-",
        entity_id=page_ctx.get("entity_id") or "-",
        visible_data_json=json.dumps(page_ctx.get("visible_data") or {}, ensure_ascii=False)[:1500],
        available_actions=_format_actions(page_ctx.get("actions") or []),
        recent_activity=recent_activity or "(no recent activity)",
        plan_first_directive=PLAN_FIRST_DIRECTIVE if plan_first else "",
    )


def chat(
    *, message: str, page_ctx: dict, project_summary: str = "",
    recent_activity: str = "", plan_first: bool = False,
    workspace_dir: str | None = None, model: str = "sonnet",
    api_key: str | None = None, max_budget_usd: float = 0.50,
    timeout_sec: int = 120,
) -> ChatResult:
    """Run one AI-sidebar chat turn."""
    sys = build_system_prompt(
        page_ctx=page_ctx, project_summary=project_summary,
        recent_activity=recent_activity, plan_first=plan_first,
    )
    full_prompt = sys + "\n" + message.strip()

    if not _claude_cli_available():
        return ChatResult(
            answer="(Claude CLI not installed on this host — AI sidebar is in stub mode. "
                   "The page context was received and a system prompt was built successfully.)",
            tool_calls=[],
            not_checked=[
                "Claude CLI is not installed — no actual LLM call was made.",
                "Response here is a placeholder, not produced by a model.",
            ],
            cost_usd=0.0, duration_ms=0, input_tokens=None, output_tokens=None,
            model_used=None,
            system_prompt=sys,
            error_kind="claude_unavailable",
            error_detail="shutil.which('claude') returned None",
        )

    # Use an ephemeral workspace (tmp) — chat doesn't need the project workspace.
    ws = workspace_dir or "."
    start = time.monotonic()
    try:
        res: CLIResult = invoke_claude(
            prompt=full_prompt, workspace_dir=ws, model=model,
            max_budget_usd=max_budget_usd, timeout_sec=timeout_sec,
            api_key=api_key,
        )
    except Exception as e:
        return ChatResult(
            answer=f"(internal error calling Claude CLI: {type(e).__name__})",
            tool_calls=[], not_checked=[f"LLM call failed: {type(e).__name__} — {e}"],
            cost_usd=0.0, duration_ms=int((time.monotonic()-start)*1000),
            input_tokens=None, output_tokens=None, model_used=None,
            system_prompt=sys, error_kind="exception", error_detail=str(e),
        )

    if res.is_error or res.return_code != 0:
        return ChatResult(
            answer=res.agent_response or "(Claude returned an error)",
            tool_calls=[], not_checked=[f"CLI exit {res.return_code}: {res.api_error_status or res.stderr[:200]}"],
            cost_usd=res.cost_usd or 0.0, duration_ms=res.duration_ms,
            input_tokens=res.input_tokens, output_tokens=res.output_tokens,
            model_used=res.model_used, system_prompt=sys,
            error_kind="cli_error", error_detail=(res.stderr or "")[:500],
        )

    text = (res.agent_response or "").strip()
    answer, not_checked = _extract_not_checked(text)
    # Tool-call surface: Claude CLI sometimes returns fenced JSON with tool_use blocks.
    # Heuristic — scan agent_response for ```tool_use or ```json blocks and lift them.
    tool_calls: list[dict] = []
    try:
        for m in re.finditer(r"```(?:tool_use|json)\s*\n(.+?)\n```", text, re.DOTALL):
            raw = m.group(1).strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and ("name" in parsed or "tool" in parsed):
                tool_calls.append({
                    "name": parsed.get("name") or parsed.get("tool") or "unknown",
                    "args": parsed.get("args") or parsed.get("input") or {},
                    "result": parsed.get("result"),
                })
    except Exception:  # pragma: no cover
        pass
    return ChatResult(
        answer=answer or "(empty response)",
        tool_calls=tool_calls,
        not_checked=not_checked,
        cost_usd=res.cost_usd or 0.0,
        duration_ms=res.duration_ms,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
        model_used=res.model_used,
        system_prompt=sys,
    )
