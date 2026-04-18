"""Autonomy levels L1–L5 (I1–I5).

L1 Assistant     — user drives every decision (default on new project)
L2 Suggests      — LLM drafts objectives/tasks, user approves
L3 Auto-within-phase — analysis→planning chain unattended; user reviews
L4 Auto-resolve  — resolves ambiguities using contract
L5 Autonomous    — full end-to-end; user reviews deliverable only

Promotion: each step requires N clean runs + 0 user overrides + audit pass since last promotion.
Veto clauses always override autonomy: conflict with MUST-constraint, budget 80%, flagged files.
"""
import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Objective, OrchestrateRun, Project
from app.models.objective_reopen import ObjectiveReopen


LEVELS = ["L1", "L2", "L3", "L4", "L5"]


PROMOTION_CRITERIA = {
    "L2": {"clean_runs_required": 0, "min_contract_chars": 0,
           "rationale": "L2 is the starting point after project setup."},
    "L3": {"clean_runs_required": 3, "min_contract_chars": 200,
           "rationale": "3 clean orchestrate runs + a non-empty operational contract."},
    "L4": {"clean_runs_required": 10, "min_contract_chars": 500,
           "rationale": "10 clean runs + substantive contract so auto-resolve has rules."},
    "L5": {"clean_runs_required": 25, "min_contract_chars": 1000,
           "rationale": "25 clean runs at L4 + substantive contract + zero re-opens in last 30d."},
}


def _clean_runs_count(db: Session, project_id: int) -> int:
    """Runs that finished DONE with no tasks_failed since last promotion."""
    proj = db.query(Project).filter(Project.id == project_id).first()
    q = db.query(OrchestrateRun).filter(
        OrchestrateRun.project_id == project_id,
        OrchestrateRun.status == "DONE",
        OrchestrateRun.tasks_failed == 0,
    )
    if proj and proj.autonomy_promoted_at:
        q = q.filter(OrchestrateRun.finished_at > proj.autonomy_promoted_at)
    return q.count()


def _reopens_last_30d(db: Session, project_id: int) -> int:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
    return db.query(ObjectiveReopen).join(
        Objective, ObjectiveReopen.objective_id == Objective.id
    ).filter(
        Objective.project_id == project_id,
        ObjectiveReopen.created_at > cutoff,
    ).count()


def current_level(project: Project) -> str:
    return project.autonomy_level or "L1"


def can_promote_to(db: Session, project: Project, target: str) -> tuple[bool, list[str]]:
    """Return (ok, blockers). Blockers are human-readable reasons."""
    if target not in LEVELS:
        return False, [f"unknown level {target}"]
    cur = current_level(project)
    if LEVELS.index(target) <= LEVELS.index(cur):
        return False, [f"already at or above {target} (current: {cur})"]
    if LEVELS.index(target) > LEVELS.index(cur) + 1:
        return False, [f"cannot skip levels: cur={cur}, requested {target}"]

    crit = PROMOTION_CRITERIA[target]
    blockers: list[str] = []

    # Clean runs
    clean = _clean_runs_count(db, project.id)
    if clean < crit["clean_runs_required"]:
        blockers.append(
            f"{clean}/{crit['clean_runs_required']} clean orchestrate runs since last promotion"
        )

    # Contract length
    contract_len = len((project.contract_md or "").strip())
    if contract_len < crit["min_contract_chars"]:
        blockers.append(
            f"operational contract too short: {contract_len}/{crit['min_contract_chars']} chars"
        )

    # L5 extra: zero re-opens in last 30d
    if target == "L5":
        reopens = _reopens_last_30d(db, project.id)
        if reopens > 0:
            blockers.append(f"{reopens} objective re-opens in last 30 days — indicates instability")

    return (len(blockers) == 0), blockers


def promote(db: Session, project: Project, target: str) -> Project:
    ok, blockers = can_promote_to(db, project, target)
    if not ok:
        raise ValueError("promotion blocked: " + "; ".join(blockers))
    project.autonomy_level = target
    project.autonomy_promoted_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return project


def veto_check(project: Project, spent_usd: float, cap_usd: float,
               files_touched: list[str]) -> list[str]:
    """Return list of veto reasons that MUST stop autonomous action."""
    vetoes: list[str] = []
    # budget
    if cap_usd and spent_usd / cap_usd > 0.80:
        vetoes.append(f"budget watermark: spent {spent_usd:.2f}/{cap_usd:.2f} (>80%)")
    # flagged paths
    flagged_defaults = {"migrations/", "billing/", "secrets/", ".env"}
    flagged = set((project.config or {}).get("veto_paths", [])) | flagged_defaults
    for p in files_touched or []:
        for fp in flagged:
            if fp in p:
                vetoes.append(f"flagged path touched: {p}")
                break
    return vetoes
