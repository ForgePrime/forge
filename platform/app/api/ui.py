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

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.cache = None  # Python 3.13 jinja2 cache hashing bug

router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    projects = []
    for p in db.query(Project).all():
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
def ui_create_project(slug: str = Form(...), name: str = Form(...), goal: str = Form(""), db: Session = Depends(get_db)):
    body = ProjectCreate(slug=slug, name=name, goal=goal or None)
    api_create_project(body, db)
    return RedirectResponse(url=f"/ui/projects/{slug}", status_code=303)


@router.get("/projects/{slug}", response_class=HTMLResponse)
def project_view(slug: str, request: Request, tab: str = Query("objectives"), db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)

    tasks = db.query(Task).filter(Task.project_id == proj.id).order_by(Task.id).all()
    by_status = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1

    objectives = []
    for o in db.query(Objective).filter(Objective.project_id == proj.id).order_by(Objective.id).all():
        objectives.append({
            "external_id": o.external_id, "title": o.title,
            "business_context": o.business_context, "status": o.status,
            "scopes": o.scopes, "priority": o.priority,
            "key_results": [{
                "position": kr.position, "text": kr.text,
                "kr_type": kr.kr_type, "status": kr.status,
                "target_value": kr.target_value, "current_value": kr.current_value,
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

    total_cost = sum(c.cost_usd or 0 for c in llm_calls)
    cost_by_purpose = {}
    for c in llm_calls:
        cost_by_purpose.setdefault(c.purpose, 0)
        cost_by_purpose[c.purpose] += c.cost_usd or 0

    return templates.TemplateResponse(request, "project.html", {
        "project": slug, "proj": proj,
        "stats": {"total_tasks": len(tasks), "tasks": by_status},
        "objectives": objectives, "tasks": tasks_view,
        "llm_calls": llm_calls, "findings": findings, "decisions": decisions,
        "knowledge": knowledge,
        "total_cost": total_cost, "cost_by_purpose": cost_by_purpose,
        "findings_count": len(findings), "decisions_count": len(decisions),
        "active_tab": tab,
    })


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
async def ui_ingest(slug: str, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    return await api_ingest(slug, files=files, db=db)


@router.post("/projects/{slug}/analyze")
def ui_analyze(slug: str, db: Session = Depends(get_db)):
    return api_analyze(slug, db)


@router.post("/projects/{slug}/plan")
def ui_plan(slug: str, objective_external_id: str = Form(...), db: Session = Depends(get_db)):
    return api_plan(slug, PlanRequest(objective_external_id=objective_external_id), db)


@router.post("/projects/{slug}/orchestrate")
def ui_orchestrate(
    slug: str,
    max_tasks: int = Form(3),
    enable_redis: str = Form(""),
    skip_infra: str = Form(""),
    db: Session = Depends(get_db),
):
    body = OrchestrateRequest(
        max_tasks=max_tasks,
        enable_redis=bool(enable_redis),
        skip_infra=bool(skip_infra),
        stop_on_failure=False,
    )
    # Long-running — return quickly, let orchestrate run async? For now sync (blocks request)
    return api_orchestrate(slug, body, db)
