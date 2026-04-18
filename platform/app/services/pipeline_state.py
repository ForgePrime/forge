"""Pipeline state detector — surfaces workflow progress to UI.

Derives four stepper states from DB: Ingest, Analyze, Plan, Orchestrate.
Each step: status (empty|done|current|blocked), summary, cta_label.
"""
from sqlalchemy.orm import Session

from app.models import Knowledge, Objective, Task, Project
from app.models.orchestrate_run import OrchestrateRun


def get_pipeline_state(db: Session, project: Project) -> dict:
    proj_id = project.id

    source_docs = db.query(Knowledge).filter(
        Knowledge.project_id == proj_id,
        Knowledge.category.in_(["source-document", "feature-spec", "requirement"]),
    ).count()

    objectives_total = db.query(Objective).filter(Objective.project_id == proj_id).count()
    objectives_active = db.query(Objective).filter(
        Objective.project_id == proj_id,
        Objective.status.in_(["ACTIVE", "NOT_STARTED", "IN_PROGRESS"]),
    ).count()

    tasks_total = db.query(Task).filter(Task.project_id == proj_id).count()
    tasks_done = db.query(Task).filter(Task.project_id == proj_id, Task.status == "DONE").count()
    tasks_failed = db.query(Task).filter(Task.project_id == proj_id, Task.status == "FAILED").count()

    active_run = db.query(OrchestrateRun).filter(
        OrchestrateRun.project_id == proj_id,
        OrchestrateRun.status.in_(["PENDING", "RUNNING"]),
    ).order_by(OrchestrateRun.id.desc()).first()
    last_run = db.query(OrchestrateRun).filter(
        OrchestrateRun.project_id == proj_id,
    ).order_by(OrchestrateRun.id.desc()).first()

    ingest = {
        "key": "ingest",
        "label": "1. Upload SOW",
        "description": "Register source documents (SOW, requirements, glossary).",
        "status": "done" if source_docs > 0 else "current",
        "summary": f"{source_docs} documents registered" if source_docs else "No documents yet",
        "cta_label": "Upload files",
    }

    if source_docs == 0:
        analyze_status = "blocked"
        analyze_summary = "Upload a SOW first"
    elif objectives_total == 0:
        analyze_status = "current"
        analyze_summary = "Ready to extract objectives"
    else:
        analyze_status = "done"
        analyze_summary = f"{objectives_total} objectives extracted"
    analyze = {
        "key": "analyze",
        "label": "2. Analyze",
        "description": "Claude extracts objectives, KRs, and open decisions from your SOW.",
        "status": analyze_status,
        "summary": analyze_summary,
        "cta_label": "Run analyze",
    }

    if objectives_total == 0:
        plan_status = "blocked"
        plan_summary = "Analyze first to get objectives"
    elif tasks_total == 0:
        plan_status = "current"
        plan_summary = f"{objectives_active} active objectives — plan one"
    else:
        plan_status = "done"
        plan_summary = f"{tasks_total} tasks ({tasks_done} done, {tasks_failed} failed)"
    plan = {
        "key": "plan",
        "label": "3. Plan",
        "description": "Decompose an objective into an executable task graph.",
        "status": plan_status,
        "summary": plan_summary,
        "cta_label": "Plan objective",
    }

    if tasks_total == 0:
        run_status = "blocked"
        run_summary = "Plan tasks first"
        run_run_id = None
    elif active_run:
        run_status = "current"
        run_summary = f"RUNNING — {active_run.tasks_completed}/{active_run.params.get('max_tasks', '?')} done"
        run_run_id = active_run.id
    elif last_run and last_run.status == "DONE":
        run_status = "done"
        run_summary = f"Last run DONE — {last_run.tasks_completed} tasks, ${last_run.total_cost_usd or 0:.2f}"
        run_run_id = last_run.id
    elif tasks_done < tasks_total:
        run_status = "current"
        run_summary = f"Ready — {tasks_total - tasks_done} tasks pending"
        run_run_id = last_run.id if last_run else None
    else:
        run_status = "done"
        run_summary = "All tasks completed"
        run_run_id = last_run.id if last_run else None
    run = {
        "key": "run",
        "label": "4. Orchestrate",
        "description": "Execute tasks end-to-end with tests, findings, and cross-model verification.",
        "status": run_status,
        "summary": run_summary,
        "cta_label": "Start run",
        "run_id": run_run_id,
        "is_running": active_run is not None,
    }

    steps = [ingest, analyze, plan, run]

    next_step = next((s for s in steps if s["status"] == "current"), None)
    return {
        "steps": steps,
        "next_step_key": next_step["key"] if next_step else None,
        "source_docs": source_docs,
        "objectives_total": objectives_total,
        "tasks_total": tasks_total,
        "tasks_done": tasks_done,
        "tasks_failed": tasks_failed,
        "active_run_id": active_run.id if active_run else None,
    }
