"""P3.2 — rough skill success-lift calculator.

Without per-task skill logs (we only bump ProjectSkill.invocations + last_used_at),
we approximate lift as: pass-rate of tasks completed AFTER the ProjectSkill row
existed vs pass-rate of tasks completed BEFORE.

This is honest-v0 polish: the resulting delta is suggestive, not proof.
Tooltip in the UI must call this out. A real lift calc requires logging the
per-task skill attribution.

Output per skill:
  {
    external_id, name,
    n_before, n_after,
    pass_rate_before, pass_rate_after,
    delta_pp,              # post - pre, in percentage points
  }"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def _rate(passed: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(passed / total * 100.0, 1)


def compute_project_skill_lifts(db: Session, project_id: int) -> list[dict[str, Any]]:
    """One row per ProjectSkill — delta pass-rate before/after attachment."""
    from app.models import ProjectSkill, Skill, Task

    ps_rows = (db.query(ProjectSkill, Skill)
                 .join(Skill, ProjectSkill.skill_id == Skill.id)
                 .filter(ProjectSkill.project_id == project_id)
                 .all())
    out: list[dict[str, Any]] = []
    for ps, sk in ps_rows:
        cutoff = ps.created_at
        # Completed tasks for this project (DONE or FAILED count as "completed attempt")
        before_q = db.query(Task).filter(
            Task.project_id == project_id,
            Task.completed_at.isnot(None),
            Task.completed_at < cutoff,
            Task.status.in_(("DONE", "FAILED")),
        )
        after_q = db.query(Task).filter(
            Task.project_id == project_id,
            Task.completed_at.isnot(None),
            Task.completed_at >= cutoff,
            Task.status.in_(("DONE", "FAILED")),
        )
        before_all = before_q.all()
        after_all = after_q.all()
        n_b = len(before_all)
        n_a = len(after_all)
        pass_b = sum(1 for t in before_all if t.status == "DONE")
        pass_a = sum(1 for t in after_all if t.status == "DONE")
        rate_b = _rate(pass_b, n_b)
        rate_a = _rate(pass_a, n_a)
        delta = None
        if rate_b is not None and rate_a is not None:
            delta = round(rate_a - rate_b, 1)
        out.append({
            "external_id": sk.external_id,
            "name": sk.name,
            "category": sk.category,
            "attach_mode": ps.attach_mode,
            "invocations": ps.invocations,
            "n_before": n_b, "n_after": n_a,
            "pass_rate_before": rate_b,
            "pass_rate_after": rate_a,
            "delta_pp": delta,
            "note": (
                "v0: approximation — compares tasks completed before vs after ProjectSkill.created_at, "
                "not per-task skill attribution."
            ),
        })
    return out
