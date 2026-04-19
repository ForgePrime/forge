"""Tier-1 backlog endpoints — operational contract, AC source attribution, objective re-open,
trust-debt counters, auto-draft docs.

Each endpoint enforces org-scoping via _assert_project_in_current_org from ui.py-style helper.
"""
import datetime as dt
import re
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AcceptanceCriterion, Decision, Finding, Knowledge, Objective, ObjectiveReopen,
    OrchestrateRun, Project, Task, User, LLMCall,
)


router = APIRouter(prefix="/api/v1/tier1", tags=["tier1"])


# -------------------- helpers --------------------

def _user(request: Request) -> User:
    u = getattr(request.state, "user", None)
    if not u:
        raise HTTPException(401, "authentication required")
    return u


def _project(db: Session, slug: str, request: Request) -> Project:
    p = db.query(Project).filter(Project.slug == slug).first()
    if not p:
        raise HTTPException(404, f"project {slug} not found")
    org = getattr(request.state, "org", None)
    if org and p.organization_id != org.id:
        raise HTTPException(403, "project not in current organization")
    return p


# ===================================================================
# G1+G3 — operational contract storage + injection
# ===================================================================

class ContractBody(BaseModel):
    contract_md: str = Field(..., max_length=20000)


# ===================================================================
# I1-I5 — Autonomy levels
# ===================================================================

@router.get("/projects/{slug}/autonomy")
def autonomy_status(slug: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    from app.services.autonomy import current_level, can_promote_to, LEVELS, PROMOTION_CRITERIA
    cur = current_level(proj)
    cur_idx = LEVELS.index(cur)
    next_level = LEVELS[cur_idx + 1] if cur_idx + 1 < len(LEVELS) else None
    status: dict = {
        "slug": slug, "current_level": cur,
        "promoted_at": proj.autonomy_promoted_at.isoformat() if proj.autonomy_promoted_at else None,
        "levels": [{"id": l, "criteria": PROMOTION_CRITERIA.get(l, {})} for l in LEVELS],
    }
    if next_level:
        ok, blockers = can_promote_to(db, proj, next_level)
        status["next"] = {"level": next_level, "eligible": ok, "blockers": blockers}
    return status


class PromoteBody(BaseModel):
    target: str = Field(..., pattern="^L[1-5]$")


@router.post("/projects/{slug}/autonomy/promote")
def autonomy_promote(slug: str, body: PromoteBody, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    from app.services.autonomy import promote
    try:
        promote(db, proj, body.target)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"slug": slug, "current_level": proj.autonomy_level}


class OptOutBody(BaseModel):
    autonomy_optout: bool


@router.put("/projects/{slug}/objectives/{external_id}/autonomy-optout")
def objective_optout(slug: str, external_id: str, body: OptOutBody,
                     request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    obj = db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == external_id
    ).first()
    if not obj:
        raise HTTPException(404, "objective not found")
    obj.autonomy_optout = body.autonomy_optout
    db.commit()
    return {"objective": external_id, "autonomy_optout": obj.autonomy_optout}


class ExecModeBody(BaseModel):
    execution_mode: str = Field(..., pattern="^(direct|crafted)$")


@router.put("/projects/{slug}/execution-mode")
def set_execution_mode(slug: str, body: ExecModeBody, request: Request, db: Session = Depends(get_db)):
    """E1 — set the project-wide execution mode: direct or crafted."""
    _user(request)
    proj = _project(db, slug, request)
    cfg = dict(proj.config or {})
    cfg["execution_mode"] = body.execution_mode
    proj.config = cfg
    db.commit()
    return {"slug": slug, "execution_mode": body.execution_mode}


@router.get("/projects/{slug}/execution-mode")
def get_execution_mode(slug: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    return {"slug": slug, "execution_mode": (proj.config or {}).get("execution_mode", "direct")}


@router.get("/projects/{slug}/contract")
def contract_get(slug: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    return {"slug": slug, "contract_md": proj.contract_md or ""}


@router.put("/projects/{slug}/contract")
def contract_put(slug: str, body: ContractBody, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    proj.contract_md = body.contract_md.strip()
    db.commit()
    return {"slug": slug, "saved": True, "length": len(proj.contract_md)}


def build_contract_injection(project: Project) -> str:
    """G3 — return the contract text to inject into LLM prompts (truncated to ~2000 tokens)."""
    md = (project.contract_md or "").strip()
    if not md:
        return ""
    # Rough: 4 chars/token. Cap at 8000 chars (~2000 tokens).
    if len(md) > 8000:
        md = md[:8000] + "\n[... truncated to 8000 chars ...]"
    return f"\n## Project operational contract (must hold in all output):\n{md}\n"


# ===================================================================
# B2 — source attribution on AC
# ===================================================================

class ACSourceBody(BaseModel):
    source_ref: str | None = Field(None, max_length=500)


@router.put("/projects/{slug}/tasks/{external_id}/ac/{position}/source")
def ac_set_source(slug: str, external_id: str, position: int, body: ACSourceBody,
                  request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    task = db.query(Task).filter(Task.project_id == proj.id, Task.external_id == external_id) \
        .order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404, f"task {external_id} not found")
    ac = db.query(AcceptanceCriterion).filter(
        AcceptanceCriterion.task_id == task.id, AcceptanceCriterion.position == position
    ).first()
    if not ac:
        raise HTTPException(404, f"AC #{position} not found")
    ac.source_ref = (body.source_ref or "").strip() or None
    db.commit()
    return {"task": external_id, "position": position,
            "source_ref": ac.source_ref, "is_unsourced": ac.source_ref is None}


@router.get("/projects/{slug}/tasks/{external_id}/ac/{position}/source-snippet")
def ac_source_snippet(slug: str, external_id: str, position: int,
                      request: Request, db: Session = Depends(get_db)):
    """Return a fragment of Knowledge.content addressed by AC.source_ref.

    Uses progressive degradation: §section → line N → keyword → head.
    Returns {snippet, source_id, selector, strategy, section_title, line_range,
    truncated, total_chars, source_title, source_url}.
    """
    _user(request)
    proj = _project(db, slug, request)
    task = db.query(Task).filter(Task.project_id == proj.id, Task.external_id == external_id) \
        .order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404, f"task {external_id} not found")
    ac = db.query(AcceptanceCriterion).filter(
        AcceptanceCriterion.task_id == task.id, AcceptanceCriterion.position == position
    ).first()
    if not ac:
        raise HTTPException(404, f"AC #{position} not found")

    from app.services.snippet_extractor import extract_snippet
    from app.models import Knowledge

    if not ac.source_ref:
        return {
            "source_id": None, "selector": None, "strategy": "no-source",
            "snippet": "(this AC has no source_ref — click the rose badge to attribute)",
            "section_title": None, "line_range": None, "truncated": False,
            "total_chars": 0, "source_title": None, "source_url": None,
        }

    src_id = ac.source_ref.split()[0].split("§")[0].strip()
    k = db.query(Knowledge).filter(
        Knowledge.project_id == proj.id, Knowledge.external_id == src_id,
    ).first()
    content = k.content if k else None
    result = extract_snippet(content, ac.source_ref)
    # Enrich with Knowledge metadata
    result["source_title"] = k.title if k else None
    result["source_url"] = f"/ui/projects/{slug}/knowledge/{k.external_id}" if k else None
    result["source_category"] = k.category if k else None
    return result


# ===================================================================
# D2 — re-open objective with notes
# ===================================================================

class ReopenBody(BaseModel):
    gap_notes: str = Field(..., min_length=20, max_length=4000)


class TaskReopenBody(BaseModel):
    gap_notes: str = Field(..., min_length=20, max_length=4000)


@router.post("/projects/{slug}/tasks/{external_id}/reopen")
def task_reopen(slug: str, external_id: str, body: TaskReopenBody,
                request: Request, db: Session = Depends(get_db)):
    """Re-open a DONE/FAILED/SKIPPED task with gap notes. Status → TODO, history preserved."""
    user = _user(request)
    proj = _project(db, slug, request)
    t = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id,
    ).order_by(Task.id.desc()).first()
    if not t:
        raise HTTPException(404, f"task {external_id} not found")
    if t.status not in ("DONE", "FAILED", "SKIPPED"):
        raise HTTPException(409, f"task is {t.status}; only DONE/FAILED/SKIPPED can be re-opened")

    prior_status = t.status
    # Store gap notes in fail_reason field (existing column, repurposed for "reopen notes")
    # Prepend the notes with a marker so they're distinguishable from original failure.
    existing = t.fail_reason or ""
    t.fail_reason = (f"[REOPEN by user_id={user.id} at {dt.datetime.now(dt.timezone.utc).isoformat()}]\n"
                     f"{body.gap_notes}\n\n---\n\n{existing}")[:8000]
    t.status = "TODO"
    t.started_at = None
    t.completed_at = None
    db.commit()
    return {"task": external_id, "status": "TODO", "prior_status": prior_status,
            "history_preserved": True}


@router.post("/projects/{slug}/objectives/{external_id}/reopen")
def objective_reopen(slug: str, external_id: str, body: ReopenBody,
                     request: Request, db: Session = Depends(get_db)):
    user = _user(request)
    proj = _project(db, slug, request)
    obj = db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == external_id
    ).first()
    if not obj:
        raise HTTPException(404, f"objective {external_id} not found")
    if obj.status not in ("ACHIEVED", "ABANDONED"):
        raise HTTPException(409, f"objective is {obj.status}; only ACHIEVED/ABANDONED can be re-opened")

    prior_state = {
        "status": obj.status,
        "kr_count": len(obj.key_results),
        "achieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    db.add(ObjectiveReopen(
        objective_id=obj.id,
        user_id=user.id,
        gap_notes=body.gap_notes.strip(),
        prior_state=prior_state,
    ))
    obj.status = "ACTIVE"
    db.commit()
    return {"objective": external_id, "status": "ACTIVE",
            "prior_status": prior_state["status"],
            "history_preserved": True}


@router.get("/projects/{slug}/objectives/{external_id}/reopens")
def objective_reopens(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    obj = db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == external_id
    ).first()
    if not obj:
        raise HTTPException(404, "objective not found")
    rows = db.query(ObjectiveReopen).filter(ObjectiveReopen.objective_id == obj.id) \
        .order_by(ObjectiveReopen.id.desc()).all()
    return {"objective": external_id,
            "reopens": [{"id": r.id, "user_id": r.user_id, "created_at": r.created_at.isoformat(),
                         "gap_notes": r.gap_notes, "prior_state": r.prior_state} for r in rows]}


# ===================================================================
# B1 — trust-debt counters (per project + org-wide)
# ===================================================================

@router.get("/projects/{slug}/trust-debt")
def trust_debt_project(slug: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    return _compute_trust_debt(db, project_id=proj.id)


@router.get("/org/triage")
def org_triage(request: Request, db: Session = Depends(get_db)):
    """K1 — org-wide triage view: what needs human judgment right now across all projects."""
    _user(request)
    org = getattr(request.state, "org", None)
    if not org:
        raise HTTPException(403, "no organization in session")
    projects = db.query(Project).filter(Project.organization_id == org.id).all()
    if not projects:
        return {"org": org.slug, "projects": [], "open_items": []}

    project_ids = [p.id for p in projects]
    open_decisions = db.query(Decision).filter(
        Decision.project_id.in_(project_ids), Decision.status == "OPEN"
    ).order_by(Decision.id.desc()).limit(50).all()
    failed_tasks = db.query(Task).filter(
        Task.project_id.in_(project_ids), Task.status == "FAILED"
    ).order_by(Task.id.desc()).limit(50).all()
    dismissed_no_reason = db.query(Finding).filter(
        Finding.project_id.in_(project_ids),
        Finding.status != "OPEN",
        Finding.dismissed_reason.is_(None),
    ).order_by(Finding.id.desc()).limit(50).all()

    # Map project_id → slug for rendering
    by_id = {p.id: p for p in projects}

    return {
        "org": org.slug,
        "projects_count": len(projects),
        "open_items": {
            "open_decisions": [
                {"project": by_id[d.project_id].slug, "id": d.external_id,
                 "severity": d.severity, "issue": (d.issue or "")[:200]}
                for d in open_decisions
            ],
            "failed_tasks": [
                {"project": by_id[t.project_id].slug, "id": t.external_id,
                 "name": t.name, "type": t.type}
                for t in failed_tasks
            ],
            "findings_dismissed_no_reason": [
                {"project": by_id[f.project_id].slug, "id": f.external_id,
                 "severity": f.severity, "title": f.title[:200]}
                for f in dismissed_no_reason
            ],
        },
    }


@router.get("/org/cross-project-patterns")
def org_cross_project_patterns(request: Request, db: Session = Depends(get_db)):
    """K2 — which skills work across multiple projects (candidate promotions to marketplace)."""
    _user(request)
    org = getattr(request.state, "org", None)
    if not org:
        raise HTTPException(403)
    from app.models import ProjectSkill, Skill
    project_ids = [p.id for p in db.query(Project).filter(Project.organization_id == org.id).all()]
    if not project_ids:
        return {"org": org.slug, "candidates": []}
    # Group attached skills, count projects
    rows = db.query(
        ProjectSkill.skill_id,
        func.count(func.distinct(ProjectSkill.project_id)).label("projects"),
        func.sum(ProjectSkill.invocations).label("invocations"),
    ).filter(ProjectSkill.project_id.in_(project_ids)) \
     .group_by(ProjectSkill.skill_id).all()
    candidates = []
    for skill_id, projects_count, invocations in rows:
        sk = db.query(Skill).filter(Skill.id == skill_id).first()
        if not sk:
            continue
        candidates.append({
            "skill_external_id": sk.external_id,
            "name": sk.name, "category": sk.category,
            "projects_attached": projects_count,
            "total_invocations": int(invocations or 0),
            "eligible_for_promotion": (projects_count >= 3 and (invocations or 0) >= 10),
        })
    candidates.sort(key=lambda c: (c["projects_attached"], c["total_invocations"]), reverse=True)
    return {"org": org.slug, "candidates": candidates}


@router.get("/org/budget-overview")
def org_budget_overview(request: Request, db: Session = Depends(get_db)):
    """K3 — aggregate org cost: per-project, per-purpose, per-user (last 30d)."""
    _user(request)
    org = getattr(request.state, "org", None)
    if not org:
        raise HTTPException(403)
    project_ids = [p.id for p in db.query(Project).filter(Project.organization_id == org.id).all()]
    if not project_ids:
        return {"org": org.slug, "per_project": [], "per_purpose": {}, "total_usd": 0}
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
    calls = db.query(LLMCall).filter(
        LLMCall.project_id.in_(project_ids),
        LLMCall.created_at > cutoff,
    ).all()
    total = sum(c.cost_usd or 0 for c in calls)
    by_proj: dict[int, float] = {}
    by_purpose: dict[str, float] = {}
    for c in calls:
        by_proj[c.project_id] = by_proj.get(c.project_id, 0) + (c.cost_usd or 0)
        by_purpose[c.purpose or "unknown"] = by_purpose.get(c.purpose or "unknown", 0) + (c.cost_usd or 0)
    proj_map = {p.id: p.slug for p in db.query(Project).filter(Project.organization_id == org.id).all()}
    return {
        "org": org.slug,
        "period": "last_30d",
        "total_usd": round(total, 4),
        "per_project": sorted(
            [{"slug": proj_map.get(pid, "?"), "cost_usd": round(v, 4)}
             for pid, v in by_proj.items()],
            key=lambda x: -x["cost_usd"],
        ),
        "per_purpose": {k: round(v, 4) for k, v in sorted(by_purpose.items(), key=lambda kv: -kv[1])},
    }


@router.get("/org/trust-debt")
def trust_debt_org(request: Request, db: Session = Depends(get_db)):
    _user(request)
    org = getattr(request.state, "org", None)
    if not org:
        raise HTTPException(403, "no organization in session")
    project_ids = [p.id for p in db.query(Project).filter(Project.organization_id == org.id).all()]
    return _compute_trust_debt(db, project_id_in=project_ids)


def _compute_trust_debt(db: Session, *, project_id: int | None = None,
                        project_id_in: list[int] | None = None) -> dict:
    """Counters of skeptical-UX debt:
    - unaudited_approvals: tasks closed (status DONE) with attempts > 0 but no recent re-review.
      Heuristic: DONE tasks where completed_at older than 7d and no comment posted on them.
    - manual_scenarios_unrun: AcceptanceCriterion.verification == 'manual' AND last_executed_at IS NULL.
    - findings_dismissed_no_reason: Finding with status='DISMISSED' (or 'CLOSED' or 'ACCEPTED'?) and no dismissed_reason.
    - stale_analyses: Objectives last analyzed > 7d ago. Heuristic: objective updated_at > 7d AND
      knowledge added since then.
    """
    # Pre-filter
    def _filter(q, model_attr):
        if project_id is not None:
            return q.filter(model_attr == project_id)
        if project_id_in is not None:
            return q.filter(model_attr.in_(project_id_in)) if project_id_in else q.filter(False)
        return q

    seven_days_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)

    # Unaudited approvals — DONE tasks older than 7d
    q_done = db.query(Task).filter(Task.status == "DONE")
    q_done = _filter(q_done, Task.project_id)
    unaudited = q_done.filter(Task.completed_at < seven_days_ago).count()

    # Manual scenarios unrun
    q_ac = db.query(AcceptanceCriterion).join(Task, AcceptanceCriterion.task_id == Task.id) \
        .filter(AcceptanceCriterion.verification == "manual",
                AcceptanceCriterion.last_executed_at.is_(None))
    q_ac = _filter(q_ac, Task.project_id)
    manual_unrun = q_ac.count()

    # Findings dismissed without reason — only those flagged dismissed but no reason text.
    # Forge has Finding.status — typical values 'OPEN','RESOLVED'. We treat any non-OPEN
    # finding without dismissed_reason as a debt entry.
    q_fd = db.query(Finding).filter(
        Finding.status != "OPEN",
        Finding.dismissed_reason.is_(None),
    )
    q_fd = _filter(q_fd, Finding.project_id)
    dismissed_no_reason = q_fd.count()

    # Stale analyses — objectives touched >7d ago whose project has new Knowledge added since
    q_obj = db.query(Objective).filter(Objective.updated_at < seven_days_ago)
    q_obj = _filter(q_obj, Objective.project_id)
    stale = 0
    for o in q_obj.all():
        # If knowledge added after objective.updated_at → analysis stale
        new_kn = db.query(Knowledge).filter(
            Knowledge.project_id == o.project_id,
            Knowledge.created_at > o.updated_at,
        ).count()
        if new_kn:
            stale += 1

    return {
        "unaudited_approvals": unaudited,
        "manual_scenarios_unrun": manual_unrun,
        "findings_dismissed_no_reason": dismissed_no_reason,
        "stale_analyses": stale,
        "computed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


class FindingDismissBody(BaseModel):
    dismissed_reason: str = Field(..., min_length=50, max_length=2000)


# ===================================================================
# CGAID in-repo artifact exports — Plan (#3) + ADRs (#5)
# ===================================================================

@router.post("/projects/{slug}/export/plan")
def export_plan(slug: str, request: Request, db: Session = Depends(get_db)):
    """Manually regenerate in-repo .ai/PLAN.md + .ai/PLAN_{O-NNN}.md from current DB state.

    Used for disaster recovery (files deleted) or initial sync on existing project.
    Idempotent — overwrites files with current state.
    """
    _user(request)
    proj = _project(db, slug, request)
    from app.services.plan_exporter import export_project_plan
    from app.config import settings as _settings
    paths = export_project_plan(db, proj, _settings.workspace_root)
    return {
        "project": slug,
        "files_written": len(paths),
        "paths": [str(p) for p in paths],
    }


@router.post("/projects/{slug}/export/adrs")
def export_adrs(slug: str, request: Request, db: Session = Depends(get_db)):
    """Manually regenerate in-repo .ai/decisions/D-NNN-*.md for every CLOSED Decision.

    Used for disaster recovery or bulk sync on project with existing decisions
    that predate the in-repo export hook. Idempotent — overwrites files.
    """
    _user(request)
    proj = _project(db, slug, request)
    from app.services.adr_exporter import export_all_closed_decisions
    from app.config import settings as _settings
    paths = export_all_closed_decisions(db, proj, _settings.workspace_root)
    return {
        "project": slug,
        "decisions_exported": len(paths),
        "paths": [str(p) for p in paths],
    }


@router.post("/projects/{slug}/export/handoff")
def export_handoff(slug: str, request: Request, db: Session = Depends(get_db)):
    """Manually regenerate in-repo .ai/handoff/HANDOFF_T-NNN-*.md for every feature/bug task.

    CGAID Artifact #4 — renders all 8 required handoff fields per task.
    Idempotent — overwrites files.
    """
    _user(request)
    proj = _project(db, slug, request)
    from app.services.handoff_exporter import export_project_handoffs
    from app.config import settings as _settings
    paths = export_project_handoffs(db, proj, _settings.workspace_root)
    return {
        "project": slug,
        "handoffs_exported": len(paths),
        "paths": [str(p) for p in paths],
    }


@router.post("/projects/{slug}/findings/{external_id}/dismiss")
def finding_dismiss(slug: str, external_id: str, body: FindingDismissBody,
                    request: Request, db: Session = Depends(get_db)):
    """Dismiss a finding with mandatory reason (>=50 chars) — closes the trust-debt loop."""
    _user(request)
    proj = _project(db, slug, request)
    f = db.query(Finding).filter(
        Finding.project_id == proj.id, Finding.external_id == external_id
    ).first()
    if not f:
        raise HTTPException(404, f"finding {external_id} not found")
    f.status = "DISMISSED"
    f.dismissed_reason = body.dismissed_reason.strip()
    f.dismissed_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return {"finding": external_id, "status": "DISMISSED",
            "reason_len": len(f.dismissed_reason)}


# ===================================================================
# L1 — auto-draft docs
# ===================================================================

# ===================================================================
# C1+C2 — Knowledge Base v0: 4 source types with descriptions
# ===================================================================

class KBAddNoteBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    description: str | None = Field(None, max_length=2000)
    focus_hint: str | None = Field(None, max_length=1000)


class KBAddURLBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    target_url: str = Field(..., min_length=8, max_length=2000)
    description: str | None = Field(None, max_length=2000)
    focus_hint: str | None = Field(None, max_length=1000)


class KBAddFolderBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    target_path: str = Field(..., min_length=1, max_length=2000)
    description: str | None = Field(None, max_length=2000)
    focus_hint: str | None = Field(None, max_length=1000)


def _next_kb_external(db: Session, project_id: int) -> str:
    last = db.query(Knowledge).filter(
        Knowledge.project_id == project_id,
        Knowledge.external_id.like("SRC-%"),
    ).order_by(Knowledge.id.desc()).first()
    if not last:
        return "SRC-001"
    try:
        num = int(last.external_id.split("-")[1]) + 1
    except (ValueError, IndexError):
        num = 1
    return f"SRC-{num:03d}"


@router.post("/projects/{slug}/kb/note")
def kb_add_note(slug: str, body: KBAddNoteBody, request: Request, db: Session = Depends(get_db)):
    """Add a manual note to the KB (e.g. verbal client constraints)."""
    _user(request)
    proj = _project(db, slug, request)
    ext = _next_kb_external(db, proj.id)
    kn = Knowledge(
        project_id=proj.id, external_id=ext,
        title=body.title, category="source-document",
        content=body.content, source_type="manual",
        description=body.description, focus_hint=body.focus_hint,
        created_by=str(getattr(request.state.user, "id", "manual")),
    )
    db.add(kn); db.commit()
    return {"external_id": ext, "source_type": "manual"}


@router.post("/projects/{slug}/kb/url")
def kb_add_url(slug: str, body: KBAddURLBody, request: Request, db: Session = Depends(get_db)):
    """Register + crawl a URL (C4). Fetches via httpx, extracts text via BeautifulSoup."""
    _user(request)
    proj = _project(db, slug, request)
    ext = _next_kb_external(db, proj.id)
    from app.services.kb_crawl import crawl_url
    result = crawl_url(body.target_url)
    if result.ok:
        content = result.content or "_empty content_"
        title = body.title or result.title or body.target_url[:100]
        warning = None
    else:
        content = f"_URL crawl failed: {result.error}_ (original: {body.target_url})"
        title = body.title
        warning = f"crawl failed: {result.error}"
    kn = Knowledge(
        project_id=proj.id, external_id=ext,
        title=title, category="source-document",
        content=content, source_type="url",
        target_url=body.target_url,
        description=body.description, focus_hint=body.focus_hint,
        created_by=str(getattr(request.state.user, "id", "manual")),
    )
    db.add(kn); db.commit()
    return {"external_id": ext, "source_type": "url",
            "target_url": body.target_url,
            "status_code": result.status_code,
            "content_chars": len(content),
            "warning": warning}


@router.post("/projects/{slug}/kb/folder")
def kb_add_folder(slug: str, body: KBAddFolderBody, request: Request, db: Session = Depends(get_db)):
    """Register + scan a local folder (C5). Recursive walk, skip binaries, respect ignores."""
    _user(request)
    proj = _project(db, slug, request)
    ext = _next_kb_external(db, proj.id)
    from app.services.kb_crawl import scan_folder
    result = scan_folder(body.target_path)
    if result.ok:
        # Join samples into a single content blob
        parts = [f"# Folder scan: {body.target_path}",
                 f"files_found={result.files_found}, text_files={result.text_files}, sampled={len(result.samples)}",
                 ""]
        for s in result.samples[:80]:  # cap render
            parts.append(f"## {s['path']} ({s['size']} bytes)")
            parts.append(s["preview"][:2000])
            parts.append("")
        content = "\n".join(parts)[:200_000]
        warning = None
    else:
        content = f"_folder scan failed: {result.error}_ (path: {body.target_path})"
        warning = result.error
    kn = Knowledge(
        project_id=proj.id, external_id=ext,
        title=body.title, category="source-document",
        content=content, source_type="folder",
        target_url=body.target_path,
        description=body.description, focus_hint=body.focus_hint,
        created_by=str(getattr(request.state.user, "id", "manual")),
    )
    db.add(kn); db.commit()
    return {"external_id": ext, "source_type": "folder",
            "target_path": body.target_path,
            "files_found": result.files_found,
            "text_files": result.text_files,
            "samples_recorded": len(result.samples),
            "warning": warning}


class KBPatchBody(BaseModel):
    description: str | None = None
    focus_hint: str | None = None


@router.patch("/projects/{slug}/kb/{external_id}")
def kb_patch(slug: str, external_id: str, body: KBPatchBody, request: Request, db: Session = Depends(get_db)):
    """Edit description/focus_hint on an existing KB source."""
    _user(request)
    proj = _project(db, slug, request)
    kn = db.query(Knowledge).filter(
        Knowledge.project_id == proj.id, Knowledge.external_id == external_id
    ).first()
    if not kn:
        raise HTTPException(404, f"KB source {external_id} not found")
    if body.description is not None:
        kn.description = body.description.strip() or None
    if body.focus_hint is not None:
        kn.focus_hint = body.focus_hint.strip() or None
    db.commit()
    return {"external_id": external_id, "description_set": kn.description is not None,
            "focus_hint_set": kn.focus_hint is not None}


# ===================================================================
# J1 — cost forensic per task
# ===================================================================

@router.get("/projects/{slug}/tasks/{external_id}/cost-forensic")
def cost_forensic(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    """Detailed cost breakdown for a task: per-LLM-call cost, retry growth, root-cause hint."""
    _user(request)
    proj = _project(db, slug, request)
    from app.models import Task, Execution, ExecutionAttempt
    t = db.query(Task).filter(Task.project_id == proj.id, Task.external_id == external_id) \
        .order_by(Task.id.desc()).first()
    if not t:
        raise HTTPException(404, f"task {external_id} not found")

    execs = db.query(Execution).filter(Execution.task_id == t.id).order_by(Execution.id).all()
    calls = db.query(LLMCall).filter(
        LLMCall.execution_id.in_([e.id for e in execs])
    ).order_by(LLMCall.id).all() if execs else []
    attempts = db.query(ExecutionAttempt).filter(
        ExecutionAttempt.execution_id.in_([e.id for e in execs])
    ).order_by(ExecutionAttempt.id).all() if execs else []

    total_cost = sum(c.cost_usd or 0 for c in calls)
    by_purpose: dict[str, dict] = {}
    for c in calls:
        p = c.purpose or "unknown"
        b = by_purpose.setdefault(p, {"cost_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0})
        b["cost_usd"] += c.cost_usd or 0
        b["calls"] += 1
        b["input_tokens"] += c.input_tokens or 0
        b["output_tokens"] += c.output_tokens or 0
    # Context growth across attempts (root cause hint)
    growth = []
    last_in = None
    for c in calls:
        in_t = c.input_tokens or 0
        delta = (in_t - last_in) if last_in is not None else 0
        growth.append({
            "call_id": c.id, "purpose": c.purpose,
            "input_tokens": in_t, "delta": delta,
            "cost_usd": round(c.cost_usd or 0, 4),
        })
        last_in = in_t
    # Root-cause hint: which purpose had biggest growth between calls
    biggest_growth = max(growth, key=lambda g: g["delta"], default=None)

    return {
        "task": external_id,
        "total_cost_usd": round(total_cost, 4),
        "calls_count": len(calls),
        "executions_count": len(execs),
        "attempts_count": len(attempts),
        "by_purpose": {k: {"cost_usd": round(v["cost_usd"], 4),
                            "calls": v["calls"],
                            "input_tokens": v["input_tokens"],
                            "output_tokens": v["output_tokens"],
                            "pct": round(100 * v["cost_usd"] / total_cost, 1) if total_cost else 0}
                       for k, v in by_purpose.items()},
        "context_growth": growth,
        "root_cause_hint": (
            f"largest context jump: +{biggest_growth['delta']} tokens at call #{biggest_growth['call_id']} "
            f"(purpose={biggest_growth['purpose']}). Likely retry with grown prompt."
        ) if biggest_growth and biggest_growth["delta"] > 1000 else
        "no significant context growth detected.",
    }


# ===================================================================
# J2 — mid-run trajectory forecast for orchestrate runs
# ===================================================================

@router.get("/orchestrate-runs/{run_id}/forecast")
def run_forecast(run_id: int, request: Request, db: Session = Depends(get_db)):
    """Project total run cost based on rolling avg of completed tasks so far."""
    _user(request)
    from app.models.orchestrate_run import OrchestrateRun
    from app.models import Task
    run = db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).first()
    if not run:
        raise HTTPException(404, f"run {run_id} not found")
    proj = db.query(Project).filter(Project.id == run.project_id).first()
    org = getattr(request.state, "org", None)
    if proj and org and proj.organization_id != org.id:
        raise HTTPException(403)
    spent = float(run.total_cost_usd or 0)
    completed = run.tasks_completed or 0
    failed = run.tasks_failed or 0
    max_tasks = (run.params or {}).get("max_tasks") or 0
    avg_per_task = (spent / completed) if completed else 0.0
    remaining = max(0, max_tasks - completed - failed)
    projected_remaining = avg_per_task * remaining
    projected_total = spent + projected_remaining
    cap = float(proj.config.get("budget_usd_per_run") or 0) if proj and proj.config else 0
    over_budget = (cap > 0 and projected_total > cap)
    return {
        "run_id": run_id,
        "spent_usd": round(spent, 4),
        "completed": completed, "failed": failed, "max_tasks": max_tasks,
        "avg_per_task_usd": round(avg_per_task, 4),
        "remaining_tasks": remaining,
        "projected_remaining_usd": round(projected_remaining, 4),
        "projected_total_usd": round(projected_total, 4),
        "cap_usd": cap,
        "over_budget_projected": over_budget,
        "warning": "projected to exceed cap — consider pausing" if over_budget else None,
    }


# ===================================================================
# J3 — reverse-trace from task → objective → KR → source attributions
# ===================================================================

@router.get("/projects/{slug}/tasks/{external_id}/reverse-trace")
def reverse_trace(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    """Walk back from a task: origin objective → KR satisfied → requirement refs → AC sources → LLM call."""
    _user(request)
    proj = _project(db, slug, request)
    from app.models import Task, Objective, AcceptanceCriterion, LLMCall, Knowledge
    t = db.query(Task).filter(Task.project_id == proj.id, Task.external_id == external_id) \
        .order_by(Task.id.desc()).first()
    if not t:
        raise HTTPException(404, f"task {external_id} not found")

    chain: list[dict] = []
    chain.append({"layer": "task", "id": t.external_id, "name": t.name,
                  "type": t.type, "status": t.status})

    # Layer 2: origin objective
    obj = None
    if t.origin:
        obj = db.query(Objective).filter(
            Objective.project_id == proj.id, Objective.external_id == t.origin
        ).first()
        if obj:
            chain.append({"layer": "objective", "id": obj.external_id,
                          "title": obj.title, "status": obj.status})
            # KR completed
            if t.completes_kr_ids:
                for kr_ref in t.completes_kr_ids:
                    chain.append({"layer": "key_result", "id": kr_ref,
                                  "via_objective": obj.external_id})

    # Layer 3: requirement refs (linked to Knowledge sources)
    if t.requirement_refs:
        for ref in t.requirement_refs:
            src_id = ref.split()[0].split("§")[0].strip()
            kn = db.query(Knowledge).filter(
                Knowledge.project_id == proj.id, Knowledge.external_id == src_id
            ).first()
            chain.append({"layer": "requirement_ref", "ref": ref,
                          "source_id": src_id,
                          "source_title": kn.title if kn else None,
                          "source_type": kn.source_type if kn else None,
                          "found": kn is not None})

    # Layer 4: AC source attributions
    for ac in t.acceptance_criteria:
        entry = {"layer": "ac", "position": ac.position, "text": ac.text[:80],
                 "source_ref": ac.source_ref, "verification": ac.verification}
        if ac.source_llm_call_id:
            llm = db.query(LLMCall).filter(LLMCall.id == ac.source_llm_call_id).first()
            if llm:
                entry["produced_by_llm_call"] = {
                    "id": llm.id, "purpose": llm.purpose,
                    "model": llm.model_used, "cost_usd": llm.cost_usd,
                }
        chain.append(entry)

    return {
        "task": external_id, "project": slug,
        "chain_length": len(chain),
        "chain": chain,
        "scope_limits": [
            "Reverse-trace stops at the LLM call layer — does not crawl prompt sections within the call.",
            "Knowledge sources may have moved/changed since the task was authored.",
            "Source attribution on AC is opt-in (B2); missing source_ref means 'no attribution recorded', not 'no source exists'.",
        ],
    }


# ===================================================================
# J6 — Replay harness
# ===================================================================

class ReplayBody(BaseModel):
    max_budget_usd: float = Field(0.50, ge=0.0, le=5.0)
    model: str = Field("sonnet", pattern="^(sonnet|opus|haiku)$")


@router.post("/llm-calls/{call_id}/replay")
def replay_llm_call(call_id: int, body: ReplayBody | None = None,
                    request: Request = None, db: Session = Depends(get_db)):
    """Re-execute an archived LLMCall with current contract + skills. Returns side-by-side diff."""
    _user(request)
    body = body or ReplayBody()
    call = db.query(LLMCall).filter(LLMCall.id == call_id).first()
    if not call:
        raise HTTPException(404, "llm_call not found")
    # Org scope
    org = getattr(request.state, "org", None)
    if call.project_id and org:
        proj = db.query(Project).filter(Project.id == call.project_id).first()
        if proj and proj.organization_id != org.id:
            raise HTTPException(403)
    if not call.full_prompt:
        raise HTTPException(422, "archived call has no full_prompt — cannot replay")

    # Re-invoke with current settings
    from app.services.claude_cli import invoke_claude
    proj = db.query(Project).filter(Project.id == call.project_id).first() if call.project_id else None
    # Refresh prompt with current contract
    prompt = call.full_prompt
    if proj and proj.contract_md:
        prompt = build_contract_injection(proj) + prompt
    workspace = "."  # no workspace-level effects
    res = invoke_claude(prompt=prompt, workspace_dir=workspace,
                       model=body.model, max_budget_usd=body.max_budget_usd,
                       timeout_sec=180)
    # Compute simple diff
    original = (call.response_text or "")[:5000]
    replayed = (res.agent_response or "")[:5000]
    same = original.strip() == replayed.strip()
    return {
        "call_id": call_id,
        "original": {
            "chars": len(call.response_text or ""),
            "cost_usd": call.cost_usd, "model": call.model_used,
            "created_at": call.started_at.isoformat() if getattr(call, "started_at", None) else None,
            "preview": original[:1000],
        },
        "replayed": {
            "chars": len(res.agent_response or ""),
            "cost_usd": res.cost_usd, "model": res.model_used,
            "preview": replayed[:1000],
        },
        "identical": same,
        "note": "Differences expected due to LLM non-determinism + newer contract/skills. Focus on *substantive* drift.",
    }


# ===================================================================
# H1 — Post-stage hooks
# ===================================================================

class HookCreateBody(BaseModel):
    stage: str = Field(..., pattern="^(after_analysis|after_planning|after_develop|after_documentation)$")
    skill_external_id: str | None = None
    purpose_text: str | None = Field(None, max_length=500)
    enabled: bool = True


@router.get("/projects/{slug}/hooks")
def list_hooks(slug: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    from app.models import ProjectHook, Skill
    rows = db.query(ProjectHook, Skill).outerjoin(
        Skill, ProjectHook.skill_id == Skill.id
    ).filter(ProjectHook.project_id == proj.id).order_by(ProjectHook.stage, ProjectHook.id).all()
    return {"slug": slug, "hooks": [{
        "id": h.id, "stage": h.stage, "enabled": h.enabled,
        "purpose_text": h.purpose_text,
        "skill": {"external_id": s.external_id, "name": s.name, "category": s.category} if s else None,
    } for h, s in rows]}


@router.post("/projects/{slug}/hooks")
def create_hook(slug: str, body: HookCreateBody, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    from app.models import ProjectHook, Skill
    skill_id = None
    if body.skill_external_id:
        sk = db.query(Skill).filter(Skill.external_id == body.skill_external_id).first()
        if not sk:
            raise HTTPException(404, f"skill {body.skill_external_id} not found")
        skill_id = sk.id
    h = ProjectHook(
        project_id=proj.id, stage=body.stage, skill_id=skill_id,
        purpose_text=body.purpose_text, enabled=body.enabled,
    )
    db.add(h); db.commit()
    return {"id": h.id, "stage": h.stage, "enabled": h.enabled}


@router.delete("/projects/{slug}/hooks/{hook_id}")
def delete_hook(slug: str, hook_id: int, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = _project(db, slug, request)
    from app.models import ProjectHook
    h = db.query(ProjectHook).filter(
        ProjectHook.id == hook_id, ProjectHook.project_id == proj.id
    ).first()
    if not h:
        raise HTTPException(404)
    db.delete(h); db.commit()
    return {"deleted": True}


# ===================================================================
# KB source-level conflict scan (from mockup 02v2)
# ===================================================================

@router.get("/projects/{slug}/kb/conflicts")
def kb_conflicts(slug: str, request: Request, db: Session = Depends(get_db)):
    """Heuristic conflict scan on KB sources: pairs where terms from one contradict another.
    V0 implementation: looks for pairs where one source contains 'on-prem' and another
    contains 'cloud'/'aws'/'azure'/'gcp' (common migration conflict). Returns pairs with
    the conflicting keywords surfaced.
    """
    _user(request)
    proj = _project(db, slug, request)
    sources = db.query(Knowledge).filter(
        Knowledge.project_id == proj.id,
        Knowledge.category == "source-document",
    ).all()
    if len(sources) < 2:
        return {"slug": slug, "conflicts": [], "scope_limit": "fewer than 2 sources — nothing to compare"}

    # Keyword conflict pairs (anti-patterns)
    antonym_pairs = [
        ({"on-prem", "onprem", "self-hosted"}, {"aws", "azure", "gcp", "cloud"}),
        ({"sql server", "mssql"}, {"postgres", "postgresql"}),
        ({"python"}, {"java", "c#", "go", "ruby"}),
        ({"monolith"}, {"microservice"}),
        ({"synchronous"}, {"asynchronous", "async"}),
        ({"oracle"}, {"mysql", "postgres", "sqlite"}),
    ]

    def content_lc(k):
        return (k.title or "").lower() + "\n" + (k.content or "").lower() + "\n" + (k.description or "").lower()

    conflicts = []
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            a = content_lc(sources[i])
            b = content_lc(sources[j])
            for left_set, right_set in antonym_pairs:
                a_hits = [w for w in left_set if w in a]
                b_hits = [w for w in right_set if w in b]
                if a_hits and b_hits:
                    conflicts.append({
                        "pair": [sources[i].external_id, sources[j].external_id],
                        "titles": [sources[i].title, sources[j].title],
                        "conflict_terms": [a_hits, b_hits],
                    })
                # Check the reverse
                a_hits2 = [w for w in right_set if w in a]
                b_hits2 = [w for w in left_set if w in b]
                if a_hits2 and b_hits2:
                    conflicts.append({
                        "pair": [sources[i].external_id, sources[j].external_id],
                        "titles": [sources[i].title, sources[j].title],
                        "conflict_terms": [a_hits2, b_hits2],
                    })
    # Deduplicate (same pair may appear twice for symmetric rules)
    seen = set()
    dedup = []
    for c in conflicts:
        key = tuple(sorted(c["pair"]))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(c)
    return {"slug": slug, "scanned": len(sources), "conflicts": dedup,
            "scope_limit": "keyword-based heuristic — false positives likely on semantically compatible phrasings."}


@router.get("/projects/{slug}/docs/auto")
def docs_auto_draft(slug: str, request: Request, db: Session = Depends(get_db)):
    """Deterministically generate a documentation snapshot from project state.

    No LLM call. Sections:
    - README (project metadata + decisions summary)
    - Changelog (DONE tasks with diffs)
    - Pipeline status (objectives + KR + tasks counts)
    - Cost ledger (per-task cost rollup)
    - Findings audit (open vs dismissed)
    """
    _user(request)
    proj = _project(db, slug, request)

    objectives = db.query(Objective).filter(Objective.project_id == proj.id) \
        .order_by(Objective.id).all()
    tasks = db.query(Task).filter(Task.project_id == proj.id).order_by(Task.id).all()
    sources = db.query(Knowledge).filter(Knowledge.project_id == proj.id).all()
    findings = db.query(Finding).filter(Finding.project_id == proj.id).all()
    runs = db.query(OrchestrateRun).filter(OrchestrateRun.project_id == proj.id) \
        .order_by(OrchestrateRun.id).all()

    total_cost = db.query(func.coalesce(func.sum(LLMCall.cost_usd), 0.0)) \
        .filter(LLMCall.project_id == proj.id).scalar() or 0.0

    # README
    readme = [
        f"# {proj.name}",
        "",
        f"**Slug:** `{proj.slug}`",
        f"**Goal:** {proj.goal or '_not set_'}",
        "",
        "## Knowledge sources",
        f"- Total: {len(sources)} document(s) registered.",
    ]
    for s in sources[:20]:
        readme.append(f"  - `{s.external_id}` · {s.category or 'note'} · {s.title or 'untitled'}")
    if len(sources) > 20:
        readme.append(f"  - … and {len(sources) - 20} more")

    # Pipeline status
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1
        by_type[t.type] = by_type.get(t.type, 0) + 1
    pipeline = [
        "",
        "## Pipeline status",
        f"- Objectives: {len(objectives)}",
        f"- Tasks: {len(tasks)} (by status: " + ", ".join(f"{k}={v}" for k, v in by_status.items()) + ")",
        "",
        "  By type: " + ", ".join(f"{k}={v}" for k, v in by_type.items()),
    ]
    for o in objectives:
        pipeline.append(f"  - `{o.external_id}` · {o.status} · {o.title}")

    # Changelog
    changelog = ["", "## Changelog (DONE tasks)"]
    done_tasks = [t for t in tasks if t.status == "DONE"]
    if not done_tasks:
        changelog.append("- _no DONE tasks yet_")
    for t in done_tasks[-30:]:
        date = t.completed_at.strftime("%Y-%m-%d") if t.completed_at else "?"
        changelog.append(f"- {date} · `{t.external_id}` · {t.name}")

    # Findings
    findings_section = [
        "", "## Findings audit",
        f"- Total: {len(findings)}",
        f"  - OPEN: {sum(1 for f in findings if f.status == 'OPEN')}",
        f"  - DISMISSED: {sum(1 for f in findings if f.status == 'DISMISSED')}",
        f"  - DISMISSED without reason: {sum(1 for f in findings if f.status == 'DISMISSED' and not f.dismissed_reason)}",
    ]

    # Cost
    cost_section = [
        "", "## Cost ledger",
        f"- Total LLM cost (all time): ${total_cost:.4f}",
        f"- Orchestrate runs executed: {len(runs)}",
    ]

    md = "\n".join(readme + pipeline + changelog + findings_section + cost_section)
    return {
        "slug": slug,
        "format": "markdown",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "deterministic": True,
        "llm_used": False,
        "content_md": md,
        "size_chars": len(md),
    }
