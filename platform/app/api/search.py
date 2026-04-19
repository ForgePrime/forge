"""⌘K global search + cross-project activity feed (mockup 01)."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Finding, Knowledge, Objective, OrchestrateRun, Project, Task, User,
)
from app.models.objective_reopen import ObjectiveReopen


router = APIRouter(prefix="/api/v1", tags=["search", "activity"])


def _user(request: Request) -> User:
    u = getattr(request.state, "user", None)
    if not u:
        raise HTTPException(401)
    return u


@router.get("/search")
def global_search(request: Request, q: str = Query(..., min_length=1, max_length=64),
                  limit: int = Query(8, ge=1, le=30),
                  db: Session = Depends(get_db)):
    """Org-scoped search across: projects · objectives · tasks · knowledge · findings.
    Results grouped by entity kind for a ⌘K picker."""
    _user(request)
    org = getattr(request.state, "org", None)
    if not org:
        return {"projects": [], "objectives": [], "tasks": [],
                "knowledge": [], "findings": []}
    q_lc = f"%{q.lower()}%"
    q_up = f"%{q.upper()}%"

    # Projects
    projects = db.query(Project).filter(
        Project.organization_id == org.id,
        or_(
            Project.name.ilike(q_lc),
            Project.slug.ilike(q_lc),
            Project.goal.ilike(q_lc),
        ),
    ).limit(limit).all()
    project_ids = [p.id for p in db.query(Project).filter(
        Project.organization_id == org.id
    ).all()]
    if not project_ids:
        project_ids = [-1]

    objectives = db.query(Objective).filter(
        Objective.project_id.in_(project_ids),
        or_(
            Objective.external_id.ilike(q_up),
            Objective.title.ilike(q_lc),
            Objective.business_context.ilike(q_lc),
        ),
    ).limit(limit).all()

    tasks = db.query(Task).filter(
        Task.project_id.in_(project_ids),
        or_(
            Task.external_id.ilike(q_up),
            Task.name.ilike(q_lc),
            Task.instruction.ilike(q_lc),
        ),
    ).limit(limit).all()

    knowledge = db.query(Knowledge).filter(
        Knowledge.project_id.in_(project_ids),
        or_(
            Knowledge.external_id.ilike(q_up),
            Knowledge.title.ilike(q_lc),
            Knowledge.description.ilike(q_lc),
        ),
    ).limit(limit).all()

    findings = db.query(Finding).filter(
        Finding.project_id.in_(project_ids),
        or_(
            Finding.external_id.ilike(q_up),
            Finding.title.ilike(q_lc),
            Finding.description.ilike(q_lc),
        ),
    ).limit(limit).all()

    proj_map = {p.id: p.slug for p in db.query(Project).filter(
        Project.organization_id == org.id
    ).all()}

    return {
        "query": q,
        "projects": [{"slug": p.slug, "name": p.name,
                      "href": f"/ui/projects/{p.slug}"} for p in projects],
        "objectives": [{"external_id": o.external_id, "title": o.title,
                        "project_slug": proj_map.get(o.project_id, "?"),
                        "href": f"/ui/projects/{proj_map.get(o.project_id, '')}/objectives/{o.external_id}"} for o in objectives],
        "tasks": [{"external_id": t.external_id, "name": t.name,
                   "type": t.type, "status": t.status,
                   "project_slug": proj_map.get(t.project_id, "?"),
                   "href": f"/ui/projects/{proj_map.get(t.project_id, '')}/tasks/{t.external_id}"} for t in tasks],
        "knowledge": [{"external_id": k.external_id, "title": k.title,
                       "source_type": k.source_type,
                       "project_slug": proj_map.get(k.project_id, "?"),
                       "href": f"/ui/projects/{proj_map.get(k.project_id, '')}?tab=knowledge"} for k in knowledge],
        "findings": [{"external_id": f.external_id, "title": f.title,
                      "severity": f.severity, "status": f.status,
                      "project_slug": proj_map.get(f.project_id, "?"),
                      "href": f"/ui/projects/{proj_map.get(f.project_id, '')}?tab=findings"} for f in findings],
    }


@router.get("/org/activity-feed")
def activity_feed(request: Request, limit: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db)):
    """Cross-project activity feed for org dashboard (mockup 01).
    Merges: task state changes · reopens · orchestrate runs · findings opened."""
    _user(request)
    org = getattr(request.state, "org", None)
    if not org:
        return {"events": []}
    projects = db.query(Project).filter(Project.organization_id == org.id).all()
    project_ids = [p.id for p in projects]
    proj_map = {p.id: p.slug for p in projects}
    if not project_ids:
        return {"events": []}

    events: list[dict] = []

    # Orchestrate runs (started / finished)
    runs = db.query(OrchestrateRun).filter(
        OrchestrateRun.project_id.in_(project_ids)
    ).order_by(OrchestrateRun.id.desc()).limit(limit * 2).all()
    for r in runs:
        events.append({
            "ts": (r.finished_at or r.started_at).isoformat() if (r.finished_at or r.started_at) else None,
            "kind": "orchestrate_run",
            "project": proj_map.get(r.project_id, "?"),
            "label": f"Run #{r.id} · {r.status} · {r.tasks_completed} done / {r.tasks_failed} failed",
            "href": f"/ui/orchestrate-runs/{r.id}",
            "severity": "info" if r.status == "DONE" else "warn" if r.status in ("FAILED", "CANCELLED", "BUDGET_EXCEEDED") else "neutral",
        })

    # Task completions + failures
    tasks = db.query(Task).filter(
        Task.project_id.in_(project_ids),
        Task.completed_at.isnot(None),
    ).order_by(Task.completed_at.desc()).limit(limit * 2).all()
    for t in tasks:
        events.append({
            "ts": t.completed_at.isoformat(),
            "kind": f"task_{t.status.lower()}",
            "project": proj_map.get(t.project_id, "?"),
            "label": f"{t.external_id} · {t.status} · {t.name[:80]}",
            "href": f"/ui/projects/{proj_map.get(t.project_id, '')}/tasks/{t.external_id}",
            "severity": "info" if t.status == "DONE" else "warn",
        })

    # Objective reopens
    reopens = db.query(ObjectiveReopen).join(
        Objective, ObjectiveReopen.objective_id == Objective.id
    ).filter(
        Objective.project_id.in_(project_ids)
    ).order_by(ObjectiveReopen.id.desc()).limit(limit).all()
    for rp in reopens:
        obj = db.query(Objective).filter(Objective.id == rp.objective_id).first()
        if not obj:
            continue
        events.append({
            "ts": rp.created_at.isoformat(),
            "kind": "objective_reopen",
            "project": proj_map.get(obj.project_id, "?"),
            "label": f"{obj.external_id} re-opened · {(rp.gap_notes or '')[:80]}",
            "href": f"/ui/projects/{proj_map.get(obj.project_id, '')}/objectives/{obj.external_id}",
            "severity": "warn",
        })

    # Findings opened
    findings = db.query(Finding).filter(
        Finding.project_id.in_(project_ids),
        Finding.status == "OPEN",
    ).order_by(Finding.id.desc()).limit(limit).all()
    for f in findings:
        events.append({
            "ts": f.created_at.isoformat() if f.created_at else None,
            "kind": "finding_opened",
            "project": proj_map.get(f.project_id, "?"),
            "label": f"{f.external_id} [{f.severity}] {f.title[:80]}",
            "href": f"/ui/projects/{proj_map.get(f.project_id, '')}?tab=findings",
            "severity": "warn" if f.severity and f.severity.upper() in ("HIGH", "CRITICAL") else "neutral",
        })

    events.sort(key=lambda e: e.get("ts") or "", reverse=True)
    return {"events": events[:limit]}
