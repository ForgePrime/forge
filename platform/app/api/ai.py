"""AI sidebar API — chat + mentions."""
import datetime as dt
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AIInteraction, Knowledge, Organization, Objective, Project, Task, User,
)
from app.services.ai_chat import chat as ai_chat_run
from app.services.slash_commands import try_handle as slash_try_handle


router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    page_ctx: dict | None = None
    plan_first: bool = False


def _current_user(request: Request) -> User | None:
    return getattr(request.state, "user", None)


def _project_from_ctx(db: Session, user: User, page_ctx: dict | None) -> Project | None:
    if not page_ctx:
        return None
    et = page_ctx.get("entity_type")
    eid = page_ctx.get("entity_id")
    if et == "project" and eid:
        p = db.query(Project).filter(Project.slug == eid).first()
        return p
    if et == "task" and eid and "route" in page_ctx:
        # extract slug from route /ui/projects/{slug}/tasks/{ext}
        m = re.match(r"/ui/projects/([^/]+)/tasks/", page_ctx.get("route") or "")
        if m:
            return db.query(Project).filter(Project.slug == m.group(1)).first()
    return None


def _build_project_summary(db: Session, project: Project | None) -> str:
    if not project:
        return ""
    objectives = db.query(Objective).filter(Objective.project_id == project.id).all()
    tasks = db.query(Task).filter(Task.project_id == project.id).all()
    sources = db.query(Knowledge).filter(
        Knowledge.project_id == project.id,
        Knowledge.category.in_(["source-document", "feature-spec", "requirement"]),
    ).count()
    by_status: dict[str, int] = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    lines = [
        f"Project: {project.slug} ({project.name})",
        f"Goal: {project.goal or '(none)'}",
        f"Knowledge sources: {sources}",
        f"Objectives: {len(objectives)} — " + ", ".join(
            f"{o.external_id}:{o.status}" for o in objectives[:10]
        ),
        f"Tasks by status: " + ", ".join(f"{k}={v}" for k, v in by_status.items()) or "no tasks",
    ]
    # G3 — inject operational contract if present
    from app.api.tier1 import build_contract_injection
    contract = build_contract_injection(project)
    if contract:
        lines.append(contract)
    # J5 — inject top anti-patterns so LLM proactively avoids repeat failures
    try:
        from app.models import AntiPattern
        org_id = project.organization_id
        aps = db.query(AntiPattern).filter(
            AntiPattern.active == True,
            (AntiPattern.organization_id == org_id) | (AntiPattern.organization_id.is_(None)),
        ).order_by(AntiPattern.times_seen.desc()).limit(5).all()
        if aps:
            lines.append("\n## Active anti-patterns (do NOT repeat these):")
            for ap in aps:
                lines.append(f"- **{ap.title}** — {ap.description[:300]}")
                if ap.correct_way:
                    lines.append(f"  ↳ Correct: {ap.correct_way[:250]}")
    except Exception:
        pass
    return "\n".join(lines)


def _recent_activity_summary(db: Session, user: User, project: Project | None) -> str:
    if not project:
        return ""
    # Last 10 AI interactions in this project
    q = db.query(AIInteraction).filter(
        AIInteraction.user_id == user.id,
        AIInteraction.project_id == project.id,
    ).order_by(AIInteraction.id.desc()).limit(10).all()
    if not q:
        return "(no prior AI sidebar activity on this project)"
    out = []
    for r in reversed(q):
        out.append(f"[{r.created_at:%H:%M}] user→ai: {r.message[:100]}")
        if r.answer:
            out.append(f"            ai: {r.answer[:100]}")
    return "\n".join(out)


@router.post("/chat")
def ai_chat(body: ChatBody, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request)
    if not user:
        raise HTTPException(401, "authentication required")

    page_ctx = body.page_ctx or {"page_id": "unknown", "title": "Forge", "route": "",
                                  "entity_type": None, "entity_id": None,
                                  "visible_data": {}, "actions": []}

    project = _project_from_ctx(db, user, page_ctx)
    org = getattr(request.state, "org", None)

    # Enforce org scoping: if the page claims a project, verify user has access.
    if project and org and project.organization_id != org.id:
        raise HTTPException(403, "project not in current organization")

    project_summary = _build_project_summary(db, project) if project else ""
    recent_activity = _recent_activity_summary(db, user, project)

    # Slash-command short-circuit — skip LLM for deterministic helpers.
    slash = slash_try_handle(db, project, body.message.strip())
    if slash is not None:
        from app.services.ai_chat import ChatResult as _CR, build_system_prompt
        # Even though we don't call the LLM, build the system prompt so audit
        # rows still contain it (incl. operational contract injection — needed
        # so an admin reviewing past chats sees what the LLM WOULD have seen).
        sys_for_audit = build_system_prompt(
            page_ctx=page_ctx, project_summary=project_summary,
            recent_activity=recent_activity, plan_first=body.plan_first,
        )
        result = _CR(
            answer=slash.answer,
            tool_calls=slash.tool_calls,
            not_checked=slash.not_checked,
            cost_usd=0.0, duration_ms=0,
            input_tokens=None, output_tokens=None, model_used="slash-command",
            system_prompt=sys_for_audit + "\n# (slash command handled deterministically — system prompt logged for audit only)\n",
        )
    else:
        result = ai_chat_run(
            message=body.message,
            page_ctx=page_ctx,
            project_summary=project_summary,
            recent_activity=recent_activity,
            plan_first=body.plan_first,
        )

    # Audit
    ai_row = AIInteraction(
        user_id=user.id,
        organization_id=org.id if org else None,
        project_id=project.id if project else None,
        page_id=page_ctx.get("page_id") or "unknown",
        entity_type=page_ctx.get("entity_type"),
        entity_id=page_ctx.get("entity_id"),
        message=body.message,
        plan_first=body.plan_first,
        page_ctx=page_ctx,
        system_prompt=result.system_prompt,
        answer=result.answer,
        tool_calls=result.tool_calls,
        not_checked=result.not_checked,
        cost_usd=result.cost_usd,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        duration_ms=result.duration_ms,
        model_used=result.model_used,
        error_kind=result.error_kind,
        error_detail=result.error_detail,
    )
    db.add(ai_row)
    db.commit()

    tokens_injected = len(result.system_prompt) // 4  # rough estimate

    return {
        "answer": result.answer,
        "tool_calls": result.tool_calls,
        "not_checked": result.not_checked,
        "cost_usd": result.cost_usd,
        "duration_ms": result.duration_ms,
        "model_used": result.model_used,
        "tokens_injected": tokens_injected,
        "error_kind": result.error_kind,
        "interaction_id": ai_row.id,
    }


@router.get("/mentions")
def ai_mentions(
    request: Request,
    q: str = Query("", max_length=64),
    project: str = Query("", max_length=64),
    db: Session = Depends(get_db),
):
    """Resolve @mention autocomplete.

    Returns list of items: {mention, label, entity_type}.
    Matches against Task.external_id, Objective.external_id, Knowledge.external_id,
    scoped to the given project slug (if any).
    """
    user = _current_user(request)
    if not user:
        raise HTTPException(401)
    items: list[dict] = []
    q_up = (q or "").upper().strip()

    if project:
        org = getattr(request.state, "org", None)
        proj = db.query(Project).filter(Project.slug == project).first()
        if not proj:
            return {"items": []}
        if org and proj.organization_id != org.id:
            raise HTTPException(403)

        # Tasks
        tasks = db.query(Task).filter(Task.project_id == proj.id)
        if q_up:
            tasks = tasks.filter(Task.external_id.ilike(f"%{q_up}%"))
        for t in tasks.limit(20).all():
            items.append({
                "mention": f"@{t.external_id}",
                "label": f"task · {t.name[:60]} · {t.status}",
                "entity_type": "task",
            })
        # Objectives
        objs = db.query(Objective).filter(Objective.project_id == proj.id)
        if q_up:
            objs = objs.filter(Objective.external_id.ilike(f"%{q_up}%"))
        for o in objs.limit(10).all():
            items.append({
                "mention": f"@{o.external_id}",
                "label": f"objective · {o.title[:60]} · {o.status}",
                "entity_type": "objective",
            })
        # Knowledge
        kn = db.query(Knowledge).filter(Knowledge.project_id == proj.id)
        if q_up:
            kn = kn.filter(Knowledge.external_id.ilike(f"%{q_up}%"))
        for k in kn.limit(10).all():
            items.append({
                "mention": f"@{k.external_id}",
                "label": f"knowledge · {k.title[:60]}",
                "entity_type": "knowledge",
            })

    return {"items": items[:30]}
