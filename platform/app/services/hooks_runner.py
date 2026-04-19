"""P1.2 — fires ProjectHooks when a task of a matching type transitions to DONE.

Contract:
  1. Map Task.type → hook stage ('analysis' → 'after_analysis', etc.).
  2. Select enabled ProjectHooks for (project_id, stage).
  3. For each hook: create a HookRun audit row.
     - If the hook has an attached Skill AND Claude CLI is available: invoke Claude
       with the skill's prompt_text as system + a concise task summary as user,
       record the llm_call_id + result preview.
     - Otherwise: record status='skipped_no_skill' / 'skipped_no_cli' so the user
       can still see the hook fired (intent) vs. silently nothing happening.
  4. Exceptions are caught — a failing hook MUST NOT crash the orchestrate loop.

This is the row that proves the user's hook configuration is actually honored."""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
import shutil
import time
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    HookRun, LLMCall, Project, ProjectHook, Skill, Task,
)

logger = logging.getLogger(__name__)


# Map Task.type → hook stage name stored on ProjectHook.stage
TASK_TYPE_TO_STAGE: dict[str, str] = {
    "analysis": "after_analysis",
    "planning": "after_planning",
    "develop": "after_develop",
    "documentation": "after_documentation",
    # Legacy aliases — match historical feature/bug/chore against after_develop
    # so existing projects see hooks fire on their common task types.
    "feature": "after_develop",
    "bug": "after_develop",
    "chore": "after_develop",
    "investigation": "after_analysis",
}


def _claude_available() -> bool:
    return shutil.which("claude") is not None


def _build_hook_prompt(task: Task, skill: Skill) -> str:
    """Small, bounded prompt for the hook LLM call."""
    ac_summary = ", ".join(ac.text[:60] for ac in (task.acceptance_criteria or [])[:5]) or "(none)"
    return (
        f"# Post-stage hook\n\n"
        f"Stage: {task.type}\n"
        f"Task: {task.external_id} — {task.name}\n"
        f"Acceptance criteria: {ac_summary}\n\n"
        f"Apply the skill below to review this just-completed task. "
        f"Be skeptical, cite evidence. Keep your reply under 300 words."
    )


def fire_hooks_for_task(
    db: Session,
    proj: Project,
    task: Task,
    *,
    workspace_dir: str | None = None,
    api_key: str | None = None,
    now: dt.datetime | None = None,
) -> list[HookRun]:
    """Fire every enabled hook that matches this task's stage. Returns the audit rows.

    MUST be called inside a try/except in the caller — or rather, any exception here
    is caught internally so orchestrate keeps running. Returns [] if no hooks match.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    stage = TASK_TYPE_TO_STAGE.get(task.type or "", None)
    if not stage:
        return []

    hooks = db.query(ProjectHook).filter(
        ProjectHook.project_id == proj.id,
        ProjectHook.stage == stage,
        ProjectHook.enabled.is_(True),
    ).all()
    if not hooks:
        return []

    runs: list[HookRun] = []
    for hook in hooks:
        t_start = time.monotonic()
        try:
            skill = db.query(Skill).filter(Skill.id == hook.skill_id).first() if hook.skill_id else None
            if skill is None:
                run = HookRun(
                    project_id=proj.id, hook_id=hook.id, task_id=task.id,
                    stage=stage, status="skipped_no_skill",
                    summary=(hook.purpose_text or "Hook has no skill attached — metadata only."),
                    started_at=now,
                    finished_at=dt.datetime.now(dt.timezone.utc),
                    duration_ms=int((time.monotonic() - t_start) * 1000),
                )
                db.add(run); db.commit(); runs.append(run)
                continue

            if not _claude_available():
                run = HookRun(
                    project_id=proj.id, hook_id=hook.id, task_id=task.id,
                    stage=stage, status="skipped_no_cli",
                    summary=f"Claude CLI not on PATH; skill {skill.external_id} would have fired.",
                    started_at=now,
                    finished_at=dt.datetime.now(dt.timezone.utc),
                    duration_ms=int((time.monotonic() - t_start) * 1000),
                )
                db.add(run); db.commit(); runs.append(run)
                continue

            # CLI available — build prompt and invoke.
            prompt = skill.prompt_text + "\n\n" + _build_hook_prompt(task, skill)
            from app.services.claude_cli import invoke_claude
            # P5.8 — default bumped from 90s (which timed out on SKILL invocations during
            # P5.4 round-2c live run) to 180s. Per-skill override wins when set.
            timeout = skill.recommended_timeout_sec or 180
            res = invoke_claude(
                prompt=prompt,
                workspace_dir=workspace_dir or ".",
                model="sonnet",
                max_budget_usd=0.20,
                timeout_sec=timeout,
                api_key=api_key,
            )
            # P5.10 fix — persist LLMCall in its OWN try block so if it fails silently
            # (observed 2026-04-19 round 2d: HookRun saved with status=fired but no
            # LLMCall row existed in DB despite apparent happy-path), we at least
            # know via the persist_err field on the HookRun row.
            prompt_chars = len(prompt)
            resp_text = (res.agent_response or "")[:20000]
            llm_id: int | None = None
            persist_err: str | None = None
            try:
                llm = LLMCall(
                    project_id=proj.id,
                    purpose=f"hook:{stage}",
                    model="sonnet",
                    model_used=res.model_used,
                    prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    prompt_chars=prompt_chars,
                    prompt_preview=prompt[:500],
                    full_prompt=prompt[:20000],
                    response_text=resp_text,
                    response_chars=len(resp_text),
                    cost_usd=res.cost_usd or 0.0,
                    duration_ms=res.duration_ms,
                    return_code=res.return_code,
                    input_tokens=res.input_tokens,
                    output_tokens=res.output_tokens,
                    is_error=res.is_error or res.return_code != 0,
                )
                db.add(llm)
                db.flush()
                # Commit the LLMCall independently so it survives regardless of
                # whatever happens to the HookRun commit below.
                db.commit()
                llm_id = llm.id
            except Exception as e:
                logger.exception("hook %s — LLMCall persist failed", hook.id)
                try:
                    db.rollback()
                except Exception:
                    pass
                persist_err = f"{type(e).__name__}: {str(e)[:200]}"

            status = "error" if (res.is_error or res.return_code != 0) else "fired"
            summary = (res.agent_response or "")[:500] or (res.stderr or "")[:500]
            if persist_err:
                summary = f"[LLMCall persist failed: {persist_err}]\n" + (summary or "")
            run = HookRun(
                project_id=proj.id, hook_id=hook.id, task_id=task.id,
                llm_call_id=llm_id,
                stage=stage, status=status,
                summary=(summary or "(empty response)")[:2000],
                started_at=now,
                finished_at=dt.datetime.now(dt.timezone.utc),
                duration_ms=int((time.monotonic() - t_start) * 1000),
            )
            db.add(run); db.commit(); runs.append(run)
        except Exception as e:  # pragma: no cover — defensive
            logger.exception("hook %s fired with exception", hook.id)
            try:
                db.rollback()
            except Exception:
                pass
            run = HookRun(
                project_id=proj.id, hook_id=hook.id, task_id=task.id,
                stage=stage, status="error",
                summary=f"{type(e).__name__}: {str(e)[:400]}",
                started_at=now,
                finished_at=dt.datetime.now(dt.timezone.utc),
                duration_ms=int((time.monotonic() - t_start) * 1000),
            )
            db.add(run); db.commit(); runs.append(run)

    return runs
