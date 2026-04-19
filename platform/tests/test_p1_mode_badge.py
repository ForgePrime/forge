"""P1.4 — Execution.mode must surface on the task report (badge + API).

The regression we're preventing: `Execution.mode` column is set during
orchestrate (direct | crafted | shadow | plan), but the task_report view
never returned it, and the HTML never rendered it. User couldn't tell
whether a DONE task actually wrote code or was a dry plan."""
import datetime as dt

import pytest

from app.database import SessionLocal
from app.models import Execution, Project, Task
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p1mode")


def _seed_accepted_exec(db, task_id: int, mode: str = "direct",
                        crafter_call_id: int | None = None) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    ex = Execution(
        task_id=task_id, agent="test",
        status="ACCEPTED", mode=mode,
        crafter_call_id=crafter_call_id,
        completed_at=now,
        lease_expires_at=now + dt.timedelta(minutes=30),
    )
    db.add(ex); db.commit(); db.refresh(ex)
    return ex.id


def test_task_report_api_exposes_latest_execution_with_mode(ps):
    """GET /api/v1/projects/{slug}/tasks/{ext}/report must return latest_execution.mode"""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        ex_id = _seed_accepted_exec(db, task.id, mode="crafted")
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/projects/{slug}/tasks/{task_ext}/report")
    assert r.status_code == 200
    j = r.json()
    assert "latest_execution" in j
    le = j["latest_execution"]
    assert le is not None
    assert le["mode"] == "crafted"
    assert le["status"] == "ACCEPTED"
    assert le["started_at"] and le["completed_at"]

    db = SessionLocal()
    try:
        db.query(Execution).filter(Execution.id == ex_id).delete()
        db.commit()
    finally:
        db.close()


def test_task_report_api_defaults_mode_to_direct_when_null(ps):
    """Legacy executions without mode set → should read as 'direct' in the payload."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        ex_id = _seed_accepted_exec(db, task.id, mode=None)  # legacy row
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/projects/{slug}/tasks/{task_ext}/report")
    assert r.status_code == 200
    le = r.json()["latest_execution"]
    assert le["mode"] == "direct"

    db = SessionLocal()
    try:
        db.query(Execution).filter(Execution.id == ex_id).delete()
        db.commit()
    finally:
        db.close()


def test_task_report_api_latest_execution_none_when_no_accepted(ps):
    """Task with no ACCEPTED execution → latest_execution should be None, not a dict with blanks."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        # Find a task with NO accepted executions
        task = db.query(Task).filter(
            Task.project_id == proj.id,
            Task.status != "DONE",
        ).first()
        if not task:
            pytest.skip("populated fixture has no non-DONE task")
        # Delete any ACCEPTED execs just in case
        db.query(Execution).filter(
            Execution.task_id == task.id,
            Execution.status == "ACCEPTED",
        ).delete()
        db.commit()
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/projects/{slug}/tasks/{task_ext}/report")
    assert r.status_code == 200
    assert r.json().get("latest_execution") is None


@pytest.mark.parametrize("mode,color_class", [
    ("direct", "bg-indigo-100"),
    ("crafted", "bg-fuchsia-100"),
    ("shadow", "bg-slate-200"),
    ("plan", "bg-sky-100"),
])
def test_task_report_html_renders_mode_badge(ps, mode, color_class):
    """Each mode must render with its distinct pill color so the user can tell them apart."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        task.status = "DONE"
        db.commit()
        ex_id = _seed_accepted_exec(db, task.id, mode=mode)
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/ui/projects/{slug}/tasks/{task_ext}")
    assert r.status_code == 200, r.text[:200]
    html = r.text
    assert f"mode: {mode}" in html, f"missing mode label for {mode}"
    assert color_class in html, f"missing color class {color_class} for mode={mode}"

    db = SessionLocal()
    try:
        db.query(Execution).filter(Execution.id == ex_id).delete()
        db.commit()
    finally:
        db.close()


def test_task_report_html_omits_badge_when_no_accepted_execution(ps):
    """If task never had an ACCEPTED execution, the mode badge must not render."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(
            Task.project_id == proj.id,
            Task.status != "DONE",
        ).first()
        if not task:
            pytest.skip("no non-DONE task available")
        db.query(Execution).filter(
            Execution.task_id == task.id,
            Execution.status == "ACCEPTED",
        ).delete()
        db.commit()
        task_ext = task.external_id
    finally:
        db.close()

    r = s.get(f"{BASE}/ui/projects/{slug}/tasks/{task_ext}")
    assert r.status_code == 200
    assert "mode: direct" not in r.text
    assert "mode: crafted" not in r.text
