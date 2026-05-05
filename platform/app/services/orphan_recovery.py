"""P5.7 — orphan-run recovery.

FastAPI's BackgroundTasks runs the orchestrate worker in-process. Any uvicorn
restart kills the worker mid-run; the OrchestrateRun row stays `status='RUNNING'`
forever because nothing reads `cancel_requested` anymore.

This module flips stale RUNNING (and PENDING never-claimed) rows to INTERRUPTED
on app startup, so the user sees the truth instead of forever-spinning UI.

Heuristic: "stale" = no DB write to the row in `STALE_AFTER_MIN` minutes.
The `progress_message` / `total_cost_usd` updates by the worker bump the row's
TimestampMixin.updated_at, so a healthy worker keeps the row "fresh".

Conservative defaults:
- STALE_AFTER_MIN = 30 → won't touch a long-running task that's still working.
- We never delete data — only flip status + set `error` to explain.
"""
from __future__ import annotations

import datetime as dt
import logging
from sqlalchemy.orm import Session

from app.validation.state_transition import commit_status_transition

logger = logging.getLogger(__name__)


STALE_AFTER_MIN = 30


def mark_orphan_runs_interrupted(db: Session, *,
                                 stale_after_min: int = STALE_AFTER_MIN,
                                 now: dt.datetime | None = None) -> list[int]:
    """Find RUNNING/PAUSED/PENDING runs whose updated_at is older than the
    threshold; flip to INTERRUPTED. Returns the list of run IDs touched.

    Idempotent — safe to call repeatedly. Failures are logged, never raised."""
    from app.models import OrchestrateRun

    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(minutes=stale_after_min)

    try:
        # Stale candidates: RUNNING/PAUSED/PENDING where the updated_at is old
        # OR (defensive) updated_at is NULL (never persisted).
        stale = (db.query(OrchestrateRun)
                   .filter(OrchestrateRun.status.in_(("RUNNING", "PAUSED", "PENDING")))
                   .filter(
                       (OrchestrateRun.updated_at == None) |
                       (OrchestrateRun.updated_at < cutoff)
                   ).all())
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("orphan-recovery: query failed: %s", e)
        return []

    touched: list[int] = []
    for run in stale:
        try:
            prev_status = run.status
            commit_status_transition(run, entity_type="orchestrate_run", target_state="INTERRUPTED")
            existing_err = (run.error or "").strip()
            note = (
                f"Orphaned at startup ({now.isoformat()}): row was '{prev_status}' "
                f"with no DB activity since {run.updated_at.isoformat() if run.updated_at else '(never)'}. "
                f"Worker thread likely killed by a previous server shutdown. "
                f"Retry the constituent tasks individually if needed."
            )
            run.error = (existing_err + "\n\n" + note).strip() if existing_err else note
            run.finished_at = now
            db.commit()
            touched.append(run.id)
            logger.info("orphan-recovery: run #%s marked INTERRUPTED (was %s)",
                        run.id, prev_status)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("orphan-recovery: failed to update run #%s: %s", run.id, e)
            try:
                db.rollback()
            except Exception:
                pass
    return touched


def release_in_progress_tasks(
    db: Session, *, project_id: int | None = None,
    now: dt.datetime | None = None,
) -> list[int]:
    """Graceful shutdown: flip every IN_PROGRESS task back to TODO.

    Called from FastAPI lifespan on shutdown. Prevents tasks from being stuck
    for the full lease duration after a restart. Orchestrate loop re-claims
    them on next iteration — idempotent, safe.

    `project_id`: optional scope. Tests MUST pass it to avoid touching other
    projects' in-flight work. Production shutdown leaves it None (everything
    is going down anyway).

    Returns list of task IDs released. Never raises — best-effort.
    """
    from app.models import Task, Execution

    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        q = db.query(Task).filter(Task.status == "IN_PROGRESS")
        if project_id is not None:
            q = q.filter(Task.project_id == project_id)
        stuck = q.all()
    except Exception as e:  # pragma: no cover
        logger.warning("release-in-progress: query failed: %s", e)
        return []

    touched: list[int] = []
    for t in stuck:
        try:
            commit_status_transition(t, entity_type="task", target_state="TODO")
            t.started_at = None
            t.agent = None
            # Release any active execution lease so the next claim doesn't collide
            (db.query(Execution)
               .filter(Execution.task_id == t.id, Execution.status.in_(("PROMPT_ASSEMBLED", "DELIVERED")))
               .update({"lease_expires_at": now}))
            db.commit()
            touched.append(t.id)
            logger.info("graceful-shutdown: task #%s released (was IN_PROGRESS)", t.id)
        except Exception as e:  # pragma: no cover
            logger.warning("graceful-shutdown: failed to release task #%s: %s", t.id, e)
            try:
                db.rollback()
            except Exception:
                pass
    return touched


def mark_running_runs_interrupted_on_shutdown(
    db: Session, *, project_id: int | None = None,
    now: dt.datetime | None = None,
) -> list[int]:
    """Graceful shutdown: flip every RUNNING/PAUSED/PENDING OrchestrateRun to INTERRUPTED.

    Unlike `mark_orphan_runs_interrupted` (startup-time, uses STALE_AFTER_MIN),
    this is called on shutdown so we know for certain the worker is going away.
    No staleness filter — everything RUNNING right now is about to be interrupted.

    `project_id`: optional scope. Tests MUST pass it to avoid marking other
    projects' live runs as interrupted. Production shutdown leaves None.

    Returns list of run IDs touched. Never raises.
    """
    from app.models import OrchestrateRun

    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        q = db.query(OrchestrateRun).filter(
            OrchestrateRun.status.in_(("RUNNING", "PAUSED", "PENDING"))
        )
        if project_id is not None:
            q = q.filter(OrchestrateRun.project_id == project_id)
        active = q.all()
    except Exception as e:  # pragma: no cover
        logger.warning("shutdown-runs: query failed: %s", e)
        return []

    touched: list[int] = []
    for run in active:
        try:
            prev = run.status
            commit_status_transition(run, entity_type="orchestrate_run", target_state="INTERRUPTED")
            run.finished_at = now
            note = (
                f"Graceful shutdown ({now.isoformat()}): server SIGTERM while run was '{prev}'. "
                f"Constituent tasks released back to TODO — re-run to resume."
            )
            existing = (run.error or "").strip()
            run.error = (existing + "\n\n" + note).strip() if existing else note
            db.commit()
            touched.append(run.id)
        except Exception as e:  # pragma: no cover
            logger.warning("shutdown-runs: failed to update run #%s: %s", run.id, e)
            try:
                db.rollback()
            except Exception:
                pass
    return touched
