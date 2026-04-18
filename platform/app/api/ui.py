"""Dashboard UI — Jinja2 templates + HTMX triggers to existing /api/v1 endpoints."""

import pathlib
from typing import Any
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.database import get_db
from app.models import (
    Project, Task, Objective, KeyResult, Knowledge, Decision, Finding,
    Execution, LLMCall, TestRun,
)
from app.api.pipeline import task_report as api_task_report, _workspace
from app.api.projects import (
    create_project as api_create_project, ProjectCreate,
)
from app.api.pipeline import (
    ingest_documents as api_ingest, analyze_documents as api_analyze,
    plan_from_objective as api_plan, orchestrate as api_orchestrate,
    PlanRequest, OrchestrateRequest,
)
from fastapi import BackgroundTasks
import datetime as dt

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.cache = None  # Python 3.13 jinja2 cache hashing bug

router = APIRouter(prefix="/ui", tags=["ui"])


def _current_org_id(request: Request) -> int | None:
    """Return current org id from request.state (set by AuthMiddleware), or None if not authenticated."""
    org = getattr(request.state, "org", None)
    return org.id if org else None


def _assert_project_in_current_org(db: Session, slug: str, request: Request) -> Project:
    """Return project IF it belongs to current org, else 404.
    Prevents tenant-A peeking at tenant-B's projects via URL guessing.
    """
    org_id = _current_org_id(request)
    p = db.query(Project).filter(Project.slug == slug).first()
    if not p:
        raise HTTPException(404)
    if p.organization_id is not None and org_id is not None and p.organization_id != org_id:
        raise HTTPException(404)  # 404 not 403 — don't leak existence
    return p


# RBAC: ranking — higher = more permissions
_ROLE_RANK = {"viewer": 1, "editor": 2, "owner": 3}


def _current_role(request: Request) -> str | None:
    return getattr(request.state, "role", None)


def _require_role(request: Request, min_role: str) -> None:
    """Raises 403 if current user's role < min_role. owner > editor > viewer."""
    current = _current_role(request)
    if not current:
        raise HTTPException(403, "No role assigned")
    if _ROLE_RANK.get(current, 0) < _ROLE_RANK.get(min_role, 999):
        raise HTTPException(403, f"Requires role '{min_role}' or higher (you have '{current}')")


# --- Auth UI (login / signup / logout) — must stay PUBLIC per middleware whitelist ---

from app.services.auth import hash_password, verify_password, create_access_token
from app.models import User, Organization, Membership
from app.config import settings as _app_settings
import datetime as _dt


@router.get("/login", response_class=HTMLResponse)
def ui_login_page(request: Request, next: str = "/ui/", error: str | None = None):
    return templates.TemplateResponse(request, "login.html", {
        "project": None, "next": next, "error": error,
    })


@router.post("/login", response_class=HTMLResponse)
def ui_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/ui/"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    DUMMY = "$2b$12$CwTycUXWue0Thq9StjUM0uJ8W9Xd3nRkJ1oUN/NqVe.q6yGGi5GZS"
    stored = user.hashed_password if user else DUMMY
    ok = verify_password(password, stored)
    if not user or not ok or not user.is_active:
        return templates.TemplateResponse(request, "login.html", {
            "project": None, "next": next, "error": "Błędny email lub hasło",
        }, status_code=401)

    user.last_login_at = _dt.datetime.now(_dt.timezone.utc)
    db.commit()

    token = create_access_token(user.id, user.email)
    safe_next = next if next.startswith("/ui/") or next == "/" else "/ui/"
    resp = RedirectResponse(url=safe_next, status_code=303)
    resp.set_cookie(
        key="forge_token", value=token,
        max_age=_app_settings.jwt_access_ttl_minutes * 60,
        httponly=True, samesite="lax",
    )
    return resp


@router.get("/signup", response_class=HTMLResponse)
def ui_signup_page(request: Request, next: str = "/ui/", error: str | None = None):
    return templates.TemplateResponse(request, "signup.html", {
        "project": None, "next": next, "error": error,
    })


@router.post("/signup", response_class=HTMLResponse)
def ui_signup_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(..., min_length=10),
    full_name: str = Form(""),
    org_slug: str = Form(""),
    org_name: str = Form(""),
    next: str = Form("/ui/"),
    db: Session = Depends(get_db),
):
    if len(password) < 10:
        return templates.TemplateResponse(request, "signup.html", {
            "project": None, "next": next, "error": "Hasło musi mieć min. 10 znaków",
        }, status_code=422)
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(request, "signup.html", {
            "project": None, "next": next, "error": "Email już zarejestrowany",
        }, status_code=409)

    user = User(email=email, hashed_password=hash_password(password),
                full_name=full_name or None)
    db.add(user)
    db.flush()

    if org_slug.strip():
        if db.query(Organization).filter(Organization.slug == org_slug.strip()).first():
            return templates.TemplateResponse(request, "signup.html", {
                "project": None, "next": next,
                "error": f"Slug organizacji '{org_slug}' jest już zajęty",
            }, status_code=409)
        org = Organization(slug=org_slug.strip(), name=(org_name or org_slug).strip())
        db.add(org)
        db.flush()
        role = "owner"
    else:
        org = db.query(Organization).filter(
            Organization.slug == _app_settings.default_org_slug
        ).first()
        if not org:
            return templates.TemplateResponse(request, "signup.html", {
                "project": None, "next": next,
                "error": "Default organization missing — skontaktuj się z administratorem",
            }, status_code=500)
        role = "editor"

    db.add(Membership(user_id=user.id, organization_id=org.id, role=role))
    db.commit()

    token = create_access_token(user.id, user.email)
    safe_next = next if next.startswith("/ui/") or next == "/" else "/ui/"
    resp = RedirectResponse(url=safe_next, status_code=303)
    resp.set_cookie(
        key="forge_token", value=token,
        max_age=_app_settings.jwt_access_ttl_minutes * 60,
        httponly=True, samesite="lax",
    )
    return resp


@router.get("/logout")
@router.post("/logout")
def ui_logout():
    resp = RedirectResponse(url="/ui/login", status_code=303)
    resp.delete_cookie("forge_token")
    return resp


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    projects = []
    org_id = _current_org_id(request)
    q = db.query(Project)
    if org_id is not None:
        q = q.filter(Project.organization_id == org_id)
    for p in q.all():
        tasks = db.query(Task).filter(Task.project_id == p.id).all()
        by_status = {}
        for t in tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1
        od = db.query(Decision).filter(Decision.project_id == p.id, Decision.status == "OPEN").count()
        of = db.query(Finding).filter(Finding.project_id == p.id, Finding.status == "OPEN").count()
        cost = db.query(sqlfunc.sum(LLMCall.cost_usd)).filter(LLMCall.project_id == p.id).scalar() or 0.0
        projects.append({
            "slug": p.slug, "name": p.name, "goal": p.goal,
            "stats": {
                "total_tasks": len(tasks), "tasks": by_status,
                "open_decisions": od, "open_findings": of,
            },
            "cost": cost,
        })
    return templates.TemplateResponse(request, "index.html", {"projects": projects, "project": None})


@router.post("/projects")
def ui_create_project(
    request: Request,
    slug: str = Form(...), name: str = Form(...), goal: str = Form(""),
    db: Session = Depends(get_db),
):
    body = ProjectCreate(slug=slug, name=name, goal=goal or None)
    result = api_create_project(body, db)
    # Assign to current org (Phase 1 — projekt tworzony przez user dostaje jego org)
    org_id = _current_org_id(request)
    if org_id:
        proj = db.query(Project).filter(Project.slug == slug).first()
        if proj and proj.organization_id is None:
            proj.organization_id = org_id
            db.commit()
    return RedirectResponse(url=f"/ui/projects/{slug}", status_code=303)


@router.get("/projects/{slug}", response_class=HTMLResponse)
def project_view(
    slug: str, request: Request,
    tab: str = Query("objectives"),
    file: str | None = Query(None),
    db: Session = Depends(get_db),
):
    proj = _assert_project_in_current_org(db, slug, request)

    tasks = db.query(Task).filter(Task.project_id == proj.id).order_by(Task.id).all()
    by_status = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1

    objectives = []
    for o in db.query(Objective).filter(Objective.project_id == proj.id).order_by(Objective.id).all():
        objectives.append({
            "id": o.id,
            "external_id": o.external_id, "title": o.title,
            "business_context": o.business_context, "status": o.status,
            "scopes": o.scopes, "priority": o.priority,
            "key_results": [{
                "position": kr.position, "text": kr.text,
                "kr_type": kr.kr_type, "status": kr.status,
                "target_value": kr.target_value, "current_value": kr.current_value,
                "measurement_command": kr.measurement_command,
                "obj_id": o.id,
            } for kr in o.key_results],
        })

    tasks_view = [{
        "id": t.id, "external_id": t.external_id, "name": t.name,
        "status": t.status, "type": t.type, "origin": t.origin,
        "ac_count": len(t.acceptance_criteria),
        "requirement_refs": t.requirement_refs, "completes_kr_ids": t.completes_kr_ids,
    } for t in tasks]

    llm_calls = db.query(LLMCall).filter(LLMCall.project_id == proj.id).order_by(LLMCall.id.desc()).all()
    findings = db.query(Finding).filter(Finding.project_id == proj.id).order_by(Finding.id.desc()).all()
    decisions = db.query(Decision).filter(Decision.project_id == proj.id).order_by(Decision.id.desc()).all()
    knowledge = db.query(Knowledge).filter(Knowledge.project_id == proj.id).order_by(Knowledge.id).all()
    from app.models import Guideline as _G
    guidelines = [{
        "external_id": g.external_id, "title": g.title, "scope": g.scope,
        "weight": g.weight, "content": g.content, "rationale": g.rationale,
    } for g in db.query(_G).filter(
        ((_G.project_id == proj.id) | (_G.project_id.is_(None))),
        _G.status == "ACTIVE",
    ).order_by(_G.weight, _G.id).all()]

    total_cost = sum(c.cost_usd or 0 for c in llm_calls)
    cost_by_purpose = {}
    for c in llm_calls:
        cost_by_purpose.setdefault(c.purpose, 0)
        cost_by_purpose[c.purpose] += c.cost_usd or 0

    # Workspace files tab — lazy load only when active
    files_data = {"files": [], "dirs": [], "truncated": False}
    current_file = None
    if tab == "files":
        from app.services.workspace_browser import list_workspace_tree, read_file
        from app.api.pipeline import _workspace as _ws
        ws = _ws(slug)
        files_data = list_workspace_tree(ws)
        if file:
            current_file = read_file(ws, file)

    return templates.TemplateResponse(request, "project.html", {
        "project": slug, "proj": proj,
        "stats": {"total_tasks": len(tasks), "tasks": by_status},
        "objectives": objectives, "tasks": tasks_view,
        "llm_calls": llm_calls, "findings": findings, "decisions": decisions,
        "knowledge": knowledge,
        "total_cost": total_cost, "cost_by_purpose": cost_by_purpose,
        "findings_count": len(findings), "decisions_count": len(decisions),
        "active_tab": tab,
        "files": files_data["files"], "dirs": files_data["dirs"],
        "truncated": files_data.get("truncated"),
        "current_file": current_file,
        "guidelines": guidelines,
    })


share_router = APIRouter(prefix="/share", tags=["share"])


@share_router.get("/{token}", response_class=HTMLResponse)
def public_share_view(token: str, request: Request, db: Session = Depends(get_db)):
    """Read-only public view via capability token. No auth required."""
    from app.models import ShareLink
    sl = db.query(ShareLink).filter(ShareLink.token == token).first()
    if not sl or sl.revoked:
        raise HTTPException(404, "Link not found or revoked")
    if sl.expires_at and sl.expires_at < dt.datetime.now(dt.timezone.utc):
        raise HTTPException(410, "Link expired")
    proj = db.query(Project).filter(Project.id == sl.project_id).first()
    if not proj:
        raise HTTPException(404)
    if sl.scope == "task" and sl.task_external_id:
        # Render task report (read-only)
        from app.api.pipeline import task_report as api_task_report
        report = api_task_report(proj.slug, sl.task_external_id, db)
        return templates.TemplateResponse(request, "task_report.html", {
            "project": proj.slug, "r": report,
            "shared_view": True,  # template can hide edit buttons if it checks
        })
    # Project-scope share — minimal view
    return HTMLResponse(content=f"<h1>Project: {proj.name}</h1><p>Shared read-only view (project scope).</p>")


@router.get("/projects/{slug}/tasks/{external_id}", response_class=HTMLResponse)
def task_view(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    # Reuse existing task_report API — returns full dict
    report = api_task_report(slug, external_id, db)
    return templates.TemplateResponse(request, "task_report.html", {
        "project": slug, "r": report,
    })


@router.get("/llm-calls/{call_id}", response_class=HTMLResponse)
def llm_call_view(call_id: int, request: Request, db: Session = Depends(get_db)):
    c = db.query(LLMCall).filter(LLMCall.id == call_id).first()
    if not c:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "llm_call.html", {"c": c, "project": None})


# --- HTMX action triggers ---

@router.post("/projects/{slug}/ingest")
async def ui_ingest(slug: str, request: Request, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    _assert_project_in_current_org(db, slug, request)
    # Must pass category explicitly — calling api_ingest without it picks up unprocessed Form() default
    return await api_ingest(slug, files=files, category="source-document", db=db)


@router.post("/projects/{slug}/analyze")
def ui_analyze(slug: str, request: Request, db: Session = Depends(get_db)):
    _assert_project_in_current_org(db, slug, request)
    return api_analyze(slug, db)


@router.post("/projects/{slug}/plan")
def ui_plan(slug: str, request: Request, objective_external_id: str = Form(...), db: Session = Depends(get_db)):
    _assert_project_in_current_org(db, slug, request)
    return api_plan(slug, PlanRequest(objective_external_id=objective_external_id), db)


@router.post("/projects/{slug}/orchestrate")
def ui_orchestrate(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    max_tasks: int = Form(3),
    enable_redis: str = Form(""),
    skip_infra: str = Form(""),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    body = OrchestrateRequest(
        max_tasks=max_tasks,
        enable_redis=bool(enable_redis),
        skip_infra=bool(skip_infra),
        stop_on_failure=False,
    )
    # Phase W6: async via BackgroundTasks. Returns redirect to live view.
    from app.api.pipeline import OrchestrateRun, _run_orchestrate_background
    proj = db.query(Project).filter(Project.slug == slug).first()
    user = getattr(request.state, "user", None)
    run = OrchestrateRun(
        project_id=proj.id,
        started_by_user_id=user.id if user else None,
        params=body.model_dump(),
        status="PENDING",
        progress_message="Queued",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(_run_orchestrate_background, slug, body.model_dump(), run.id)
    return RedirectResponse(url=f"/ui/orchestrate-runs/{run.id}?project={slug}", status_code=303)


@router.get("/orchestrate-runs/{run_id}", response_class=HTMLResponse)
def ui_orchestrate_run_page(run_id: int, request: Request, project: str = Query(...), db: Session = Depends(get_db)):
    _assert_project_in_current_org(db, project, request)
    return templates.TemplateResponse(request, "orchestrate_run.html", {
        "run_id": run_id, "project": project,
    })


@router.get("/orchestrate-runs/{run_id}/panel", response_class=HTMLResponse)
def ui_orchestrate_run_panel(run_id: int, request: Request, db: Session = Depends(get_db)):
    from app.api.pipeline import OrchestrateRun
    run = db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).first()
    if not run:
        raise HTTPException(404)
    proj = db.query(Project).filter(Project.id == run.project_id).first()
    _assert_project_in_current_org(db, proj.slug, request)
    elapsed_sec = None
    if run.started_at:
        end = run.finished_at or dt.datetime.now(dt.timezone.utc)
        elapsed_sec = int((end - run.started_at).total_seconds())
    return templates.TemplateResponse(request, "_orchestrate_panel.html", {
        "r": {
            "id": run.id, "status": run.status,
            "started_at": run.started_at, "finished_at": run.finished_at,
            "elapsed_sec": elapsed_sec,
            "current_task_external_id": run.current_task_external_id,
            "current_phase": run.current_phase,
            "progress_message": run.progress_message,
            "tasks_completed": run.tasks_completed,
            "tasks_failed": run.tasks_failed,
            "total_cost_usd": run.total_cost_usd,
            "params": run.params,
            "error": run.error,
            "result": run.result,
        },
        "project": proj.slug,
    })


@router.post("/orchestrate-runs/{run_id}/cancel")
def ui_orchestrate_run_cancel(run_id: int, request: Request, db: Session = Depends(get_db)):
    from app.api.pipeline import OrchestrateRun
    run = db.query(OrchestrateRun).filter(OrchestrateRun.id == run_id).first()
    if not run:
        raise HTTPException(404)
    proj = db.query(Project).filter(Project.id == run.project_id).first()
    _assert_project_in_current_org(db, proj.slug, request)
    if run.status not in ("DONE", "FAILED", "CANCELLED", "BUDGET_EXCEEDED"):
        run.cancel_requested = True
        db.commit()
    return HTMLResponse(content="", status_code=200)


# ---------- HTMX fragments: objectives / tasks / KRs / findings ----------

def _obj_to_dict(o: Objective) -> dict:
    return {
        "id": o.id, "external_id": o.external_id, "title": o.title,
        "business_context": o.business_context, "status": o.status,
        "scopes": o.scopes, "priority": o.priority,
        "key_results": [{
            "position": kr.position, "text": kr.text, "kr_type": kr.kr_type,
            "status": kr.status, "target_value": kr.target_value,
            "current_value": kr.current_value,
            "measurement_command": kr.measurement_command, "obj_id": o.id,
        } for kr in o.key_results],
    }


def _task_to_dict(t: Task) -> dict:
    return {
        "id": t.id, "external_id": t.external_id, "name": t.name,
        "instruction": t.instruction, "description": t.description,
        "status": t.status, "type": t.type, "origin": t.origin,
        "scopes": t.scopes or [],
        "requirement_refs": t.requirement_refs or [],
        "completes_kr_ids": t.completes_kr_ids or [],
        "ac_count": len(t.acceptance_criteria),
    }


@router.get("/projects/{slug}/objectives/{external_id}/card", response_class=HTMLResponse)
def ui_objective_card(
    slug: str, external_id: str, request: Request,
    edit: int = Query(0), db: Session = Depends(get_db),
):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    o = db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == external_id
    ).first()
    if not o:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "_objective_card.html", {
        "o": _obj_to_dict(o), "project": slug, "edit": bool(edit),
    })


@router.patch("/projects/{slug}/objectives/{external_id}", response_class=HTMLResponse)
def ui_objective_patch(
    slug: str, external_id: str, request: Request,
    title: str = Form(...),
    business_context: str = Form(...),
    priority: int = Form(3),
    status: str = Form("ACTIVE"),
    scopes: str = Form(""),
    db: Session = Depends(get_db),
):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    o = db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == external_id
    ).first()
    if not o:
        raise HTTPException(404)
    o.title = title
    o.business_context = business_context
    o.priority = priority
    o.status = status
    o.scopes = [s.strip() for s in scopes.split(",") if s.strip()]
    db.commit()
    return templates.TemplateResponse(request, "_objective_card.html", {
        "o": _obj_to_dict(o), "project": slug, "edit": False,
    })


@router.get("/objectives/{obj_id}/key-results/{kr_position}/row", response_class=HTMLResponse)
def ui_kr_row(
    obj_id: int, kr_position: int, request: Request,
    edit: int = Query(0),
    obj_ext: str = Query(...),
    project: str = Query(...),
    db: Session = Depends(get_db),
):
    kr = db.query(KeyResult).filter(
        KeyResult.objective_id == obj_id, KeyResult.position == kr_position
    ).first()
    if not kr:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "_kr_row.html", {
        "o": {"external_id": obj_ext},
        "kr": {
            "position": kr.position, "text": kr.text, "kr_type": kr.kr_type,
            "status": kr.status, "target_value": kr.target_value,
            "current_value": kr.current_value,
            "measurement_command": kr.measurement_command, "obj_id": obj_id,
        },
        "project": project,
        "kr_edit": kr.position if edit else None,
    })


@router.patch("/objectives/{obj_id}/key-results/{kr_position}", response_class=HTMLResponse)
def ui_kr_patch(
    obj_id: int, kr_position: int, request: Request,
    obj_ext: str = Query(...),
    project: str = Query(...),
    text: str = Form(...),
    status: str = Form("NOT_STARTED"),
    target_value: str = Form(""),
    current_value: str = Form(""),
    measurement_command: str = Form(""),
    db: Session = Depends(get_db),
):
    kr = db.query(KeyResult).filter(
        KeyResult.objective_id == obj_id, KeyResult.position == kr_position
    ).first()
    if not kr:
        raise HTTPException(404)
    kr.text = text
    kr.status = status
    kr.target_value = float(target_value) if target_value.strip() else None
    kr.current_value = float(current_value) if current_value.strip() else None
    kr.measurement_command = measurement_command.strip() or None
    db.commit()
    return templates.TemplateResponse(request, "_kr_row.html", {
        "o": {"external_id": obj_ext},
        "kr": {
            "position": kr.position, "text": kr.text, "kr_type": kr.kr_type,
            "status": kr.status, "target_value": kr.target_value,
            "current_value": kr.current_value,
            "measurement_command": kr.measurement_command, "obj_id": obj_id,
        },
        "project": project,
        "kr_edit": None,
    })


@router.get("/projects/{slug}/tasks/{external_id}/row", response_class=HTMLResponse)
def ui_task_row(
    slug: str, external_id: str, request: Request,
    edit: int = Query(0), db: Session = Depends(get_db),
):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    t = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not t:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "_task_row.html", {
        "t": _task_to_dict(t), "project": slug, "edit": bool(edit),
    })


@router.patch("/projects/{slug}/tasks/{external_id}", response_class=HTMLResponse)
def ui_task_patch(
    slug: str, external_id: str, request: Request,
    name: str = Form(...),
    instruction: str = Form(""),
    scopes: str = Form(""),
    requirement_refs: str = Form(""),
    completes_kr_ids: str = Form(""),
    db: Session = Depends(get_db),
):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    t = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not t:
        raise HTTPException(404)
    t.name = name
    t.instruction = instruction or None
    t.scopes = [s.strip() for s in scopes.split(",") if s.strip()]
    t.requirement_refs = [s.strip() for s in requirement_refs.split(";") if s.strip()]
    t.completes_kr_ids = [s.strip() for s in completes_kr_ids.split(",") if s.strip()]
    db.commit()
    return templates.TemplateResponse(request, "_task_row.html", {
        "t": _task_to_dict(t), "project": slug, "edit": False,
    })


# ---------- Org settings (Anthropic key + budget) ----------

def _org_settings_ctx(request: Request, db: Session) -> dict:
    org_obj = getattr(request.state, "org", None)
    if not org_obj:
        return {"org": None, "has_key": False, "current_month_spend": 0.0}
    # Reload fresh from DB (request.state.org is detached)
    fresh_org = db.query(Organization).filter(Organization.id == org_obj.id).first()
    # Current month spend
    import datetime as _dt
    first = _dt.datetime.now(_dt.timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spend = db.query(sqlfunc.sum(LLMCall.cost_usd)).join(
        Project, Project.id == LLMCall.project_id
    ).filter(
        Project.organization_id == fresh_org.id,
        LLMCall.created_at >= first,
    ).scalar() or 0.0
    return {
        "org": fresh_org,
        "has_key": bool(fresh_org.anthropic_api_key_encrypted),
        "current_month_spend": float(spend),
    }


@router.get("/org/settings", response_class=HTMLResponse)
def ui_org_settings(request: Request, db: Session = Depends(get_db)):
    ctx = _org_settings_ctx(request, db)
    if not ctx["org"]:
        raise HTTPException(403, "No org in session")
    # Wrap with id for HTMX target
    return HTMLResponse(content='<div id="org-settings">' +
        templates.get_template("_org_settings.html").render(**ctx) +
        '</div>')


@router.post("/org/settings/anthropic-key", response_class=HTMLResponse)
def ui_org_set_key(
    request: Request,
    api_key: str = Form(...),
    db: Session = Depends(get_db),
):
    from app.services.auth import encrypt_secret
    ctx = _org_settings_ctx(request, db)
    org = ctx["org"]
    if not org:
        raise HTTPException(403)
    if not api_key.strip():
        raise HTTPException(422, "Empty key")
    org.anthropic_api_key_encrypted = encrypt_secret(api_key.strip())
    db.commit()
    ctx = _org_settings_ctx(request, db)
    return HTMLResponse(content='<div id="org-settings">' +
        templates.get_template("_org_settings.html").render(**ctx) +
        '</div>')


@router.delete("/org/settings/anthropic-key", response_class=HTMLResponse)
def ui_org_del_key(request: Request, db: Session = Depends(get_db)):
    ctx = _org_settings_ctx(request, db)
    org = ctx["org"]
    if not org:
        raise HTTPException(403)
    org.anthropic_api_key_encrypted = None
    db.commit()
    ctx = _org_settings_ctx(request, db)
    return HTMLResponse(content='<div id="org-settings">' +
        templates.get_template("_org_settings.html").render(**ctx) +
        '</div>')


@router.post("/org/settings/budget", response_class=HTMLResponse)
def ui_org_set_budget(
    request: Request,
    budget_usd_monthly: str = Form(""),
    db: Session = Depends(get_db),
):
    ctx = _org_settings_ctx(request, db)
    org = ctx["org"]
    if not org:
        raise HTTPException(403)
    org.budget_usd_monthly = float(budget_usd_monthly) if budget_usd_monthly.strip() else None
    db.commit()
    ctx = _org_settings_ctx(request, db)
    return HTMLResponse(content='<div id="org-settings">' +
        templates.get_template("_org_settings.html").render(**ctx) +
        '</div>')


@router.post("/projects/{slug}/objectives/new")
def ui_add_objective(
    slug: str, request: Request,
    title: str = Form(...),
    business_context: str = Form(...),
    priority: int = Form(3),
    external_id: str = Form(""),
    scopes: str = Form(""),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import add_objective_single, ObjectiveCreateSingle
    add_objective_single(slug, ObjectiveCreateSingle(
        external_id=external_id.strip() or None,
        title=title, business_context=business_context,
        priority=priority,
        scopes=[s.strip() for s in scopes.split(",") if s.strip()],
    ), db)
    return RedirectResponse(url=f"/ui/projects/{slug}?tab=objectives", status_code=303)


@router.post("/projects/{slug}/tasks/new")
def ui_add_task(
    slug: str, request: Request,
    name: str = Form(...),
    type: str = Form("feature"),
    instruction: str = Form(""),
    external_id: str = Form(""),
    origin: str = Form(""),
    scopes: str = Form(""),
    completes_kr_ids: str = Form(""),
    requirement_refs: str = Form(""),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import add_task_single, TaskCreateSingle
    add_task_single(slug, TaskCreateSingle(
        external_id=external_id.strip() or None,
        name=name, instruction=instruction or None,
        type=type, origin=origin.strip() or None,
        scopes=[s.strip() for s in scopes.split(",") if s.strip()],
        completes_kr_ids=[s.strip() for s in completes_kr_ids.split(",") if s.strip()] or None,
        requirement_refs=[s.strip() for s in requirement_refs.split(";") if s.strip()] or None,
    ), db)
    return RedirectResponse(url=f"/ui/projects/{slug}?tab=tasks", status_code=303)


@router.post("/objectives/{obj_id}/key-results", response_class=HTMLResponse)
def ui_add_kr(
    obj_id: int, request: Request,
    text: str = Form(..., min_length=5),
    kr_type: str = Form("descriptive"),
    target_value: str = Form(""),
    measurement_command: str = Form(""),
    project: str = Query(...),
    obj_ext: str = Query(...),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, project, request)
    from app.api.projects import add_kr as api_add_kr, KRAdd
    tv = float(target_value) if target_value.strip() else None
    if kr_type == "numeric" and tv is None:
        raise HTTPException(422, "numeric KR wymaga target_value")
    result = api_add_kr(obj_id, KRAdd(
        text=text, kr_type=kr_type,
        target_value=tv,
        measurement_command=measurement_command.strip() or None,
    ), db)
    return templates.TemplateResponse(request, "_kr_row.html", {
        "o": {"external_id": obj_ext},
        "kr": {
            "position": result["position"], "text": text, "kr_type": kr_type,
            "status": "NOT_STARTED", "target_value": tv, "current_value": None,
            "measurement_command": measurement_command or None, "obj_id": obj_id,
        },
        "project": project, "kr_edit": None,
    })


@router.get("/projects/{slug}/tasks/{external_id}/ac/{position}/row", response_class=HTMLResponse)
def ui_ac_row(
    slug: str, external_id: str, position: int, request: Request,
    edit: int = Query(0), db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.models import AcceptanceCriterion
    proj = db.query(Project).filter(Project.slug == slug).first()
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    ac = db.query(AcceptanceCriterion).filter(
        AcceptanceCriterion.task_id == task.id, AcceptanceCriterion.position == position
    ).first()
    if not ac:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "_ac_row.html", {
        "ac": {
            "position": ac.position, "text": ac.text,
            "scenario_type": ac.scenario_type, "verification": ac.verification,
            "test_path": ac.test_path, "command": ac.command,
        },
        "task_ext": external_id, "project": slug,
        "ac_edit": position if edit else None,
    })


@router.post("/projects/{slug}/tasks/{external_id}/ac", response_class=HTMLResponse)
def ui_ac_add(
    slug: str, external_id: str, request: Request,
    text: str = Form(..., min_length=20),
    scenario_type: str = Form("positive"),
    verification: str = Form("manual"),
    test_path: str = Form(""),
    command: str = Form(""),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import add_ac as api_add_ac, ACCreate
    result = api_add_ac(slug, external_id, ACCreate(
        text=text, scenario_type=scenario_type, verification=verification,
        test_path=test_path or None, command=command or None,
    ), db)
    # Render newly created AC row (read mode)
    return templates.TemplateResponse(request, "_ac_row.html", {
        "ac": {
            "position": result["position"], "text": text,
            "scenario_type": scenario_type, "verification": verification,
            "test_path": test_path or None, "command": command or None,
        },
        "task_ext": external_id, "project": slug, "ac_edit": None,
    })


@router.patch("/projects/{slug}/tasks/{external_id}/ac/{position}", response_class=HTMLResponse)
def ui_ac_patch(
    slug: str, external_id: str, position: int, request: Request,
    text: str = Form(..., min_length=20),
    scenario_type: str = Form("positive"),
    verification: str = Form("manual"),
    test_path: str = Form(""),
    command: str = Form(""),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import update_ac as api_update_ac, ACUpdate
    api_update_ac(slug, external_id, position, ACUpdate(
        text=text, scenario_type=scenario_type, verification=verification,
        test_path=test_path or None, command=command or None,
    ), db)
    return templates.TemplateResponse(request, "_ac_row.html", {
        "ac": {
            "position": position, "text": text,
            "scenario_type": scenario_type, "verification": verification,
            "test_path": test_path or None, "command": command or None,
        },
        "task_ext": external_id, "project": slug, "ac_edit": None,
    })


@router.delete("/projects/{slug}/tasks/{external_id}/ac/{position}", response_class=HTMLResponse)
def ui_ac_delete(
    slug: str, external_id: str, position: int, request: Request,
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import delete_ac as api_delete_ac
    api_delete_ac(slug, external_id, position, db)
    return HTMLResponse(content="", status_code=200)  # HTMX hx-swap="delete" removes element


@router.post("/projects/{slug}/guidelines", response_class=HTMLResponse)
def ui_add_guideline(
    slug: str, request: Request,
    title: str = Form(...),
    content: str = Form(...),
    weight: str = Form("should"),
    scope: str = Form("general"),
    rationale: str = Form(""),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import add_guideline_single, GuidelineCreate
    add_guideline_single(slug, GuidelineCreate(
        external_id="", title=title, scope=scope or "general",
        content=content, rationale=rationale or None, weight=weight,
    ), db)
    return HTMLResponse(content="ok", status_code=200)


@router.get("/projects/{slug}/guidelines/{external_id}/card", response_class=HTMLResponse)
def ui_guideline_card(slug: str, external_id: str, request: Request, edit: int = Query(0), db: Session = Depends(get_db)):
    _assert_project_in_current_org(db, slug, request)
    from app.models import Guideline
    proj = db.query(Project).filter(Project.slug == slug).first()
    g = db.query(Guideline).filter(
        ((Guideline.project_id == proj.id) | (Guideline.project_id.is_(None))),
        Guideline.external_id == external_id,
    ).first()
    if not g:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "_guideline_card.html", {
        "g": {
            "external_id": g.external_id, "title": g.title, "scope": g.scope,
            "weight": g.weight, "content": g.content, "rationale": g.rationale,
        },
        "project": slug, "g_edit": bool(edit),
    })


@router.patch("/projects/{slug}/guidelines/{external_id}", response_class=HTMLResponse)
def ui_guideline_patch(
    slug: str, external_id: str, request: Request,
    title: str = Form(...),
    content: str = Form(...),
    weight: str = Form("should"),
    scope: str = Form("general"),
    rationale: str = Form(""),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import update_guideline, GuidelineUpdate
    update_guideline(slug, external_id, GuidelineUpdate(
        title=title, content=content, weight=weight, scope=scope, rationale=rationale or None,
    ), db)
    from app.models import Guideline
    proj = db.query(Project).filter(Project.slug == slug).first()
    g = db.query(Guideline).filter(
        ((Guideline.project_id == proj.id) | (Guideline.project_id.is_(None))),
        Guideline.external_id == external_id,
    ).first()
    return templates.TemplateResponse(request, "_guideline_card.html", {
        "g": {
            "external_id": g.external_id, "title": g.title, "scope": g.scope,
            "weight": g.weight, "content": g.content, "rationale": g.rationale,
        },
        "project": slug, "g_edit": False,
    })


@router.delete("/projects/{slug}/guidelines/{external_id}", response_class=HTMLResponse)
def ui_guideline_delete(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import delete_guideline as api_del
    api_del(slug, external_id, db)
    return HTMLResponse(content="", status_code=200)


@router.get("/projects/{slug}/tasks/{external_id}/comments", response_class=HTMLResponse)
def ui_list_comments(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    _assert_project_in_current_org(db, slug, request)
    from app.api.projects import list_comments
    cmts = list_comments(slug, external_id, db)
    if not cmts:
        return HTMLResponse(content='<li class="text-slate-400 italic">Brak komentarzy</li>')
    html = ""
    for c in cmts:
        ts = (c['created_at'] or '')[:19]
        html += f"""<li class="bg-slate-50 rounded p-2 border-l-2 border-blue-300">
            <div class="text-xs text-slate-500 mb-1 flex justify-between">
                <span>{c['user_email']}</span>
                <span class="mono">{ts}</span>
            </div>
            <div class="whitespace-pre-wrap">{c['content']}</div>
        </li>"""
    return HTMLResponse(content=html)


@router.post("/projects/{slug}/tasks/{external_id}/comments", response_class=HTMLResponse)
def ui_add_comment(
    slug: str, external_id: str, request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    _assert_project_in_current_org(db, slug, request)
    from app.models import TaskComment
    proj = db.query(Project).filter(Project.slug == slug).first()
    task = db.query(Task).filter(Task.project_id == proj.id, Task.external_id == external_id).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    user = getattr(request.state, "user", None)
    c = TaskComment(
        task_id=task.id,
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        content=content,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    user_label = (user.email if user else "anonymous")
    ts = c.created_at.isoformat()[:19] if c.created_at else ""
    return HTMLResponse(content=f"""<li class="bg-slate-50 rounded p-2 border-l-2 border-blue-300">
        <div class="text-xs text-slate-500 mb-1 flex justify-between">
            <span>{user_label}</span>
            <span class="mono">{ts}</span>
        </div>
        <div class="whitespace-pre-wrap">{content}</div>
    </li>""")


@router.post("/findings/{finding_id}/triage", response_class=HTMLResponse)
def ui_finding_triage(
    finding_id: int, request: Request,
    action: str = Form(...),
    reason: str = Form(""),
    db: Session = Depends(get_db),
):
    from app.api.projects import FindingTriageRequest, triage_finding as api_triage
    api_triage(finding_id, FindingTriageRequest(
        action=action, reason=reason or None,
    ), db)
    # Reload finding + render card
    f = db.query(Finding).filter(Finding.id == finding_id).first()
    return templates.TemplateResponse(request, "_finding_card.html", {
        "f": f, "project": None,
    })
