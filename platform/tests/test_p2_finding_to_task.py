"""P2.1 — Finding → Task one-click.

Mockup 05v2 promised a `→ Task` button on findings that creates a chore task.
These tests prove: endpoint creates a task with origin_finding_id set,
idempotency (second click returns the existing task), dismissed findings
rejected, origin chip surfaces on task_report payload + HTML."""
import pytest

from app.database import SessionLocal
from app.models import Finding, Project, Task
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p2find")


def _seed_finding(db, proj_id: int, status: str = "OPEN",
                  title: str = "SQL injection risk in /search",
                  severity: str = "HIGH") -> str:
    from app.api.pipeline import _next_external_id as _nxt
    ext = _nxt(db, proj_id, Finding, "F")
    f = Finding(
        project_id=proj_id, external_id=ext,
        type="bug", severity=severity, title=title,
        description="Concatenated user input into SQL query at app/search.py:42",
        suggested_action="Use parameterized queries (SQLAlchemy bindparam).",
        status=status,
    )
    db.add(f); db.commit()
    return ext


def test_create_task_from_finding_success(ps):
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ext = _seed_finding(db, proj.id)
    finally:
        db.close()

    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/{ext}/create-task")
    assert r.status_code == 200
    j = r.json()
    assert j["created"] is True
    assert j["status"] == "TODO"
    task_ext = j["task_external_id"]

    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        t = db.query(Task).filter(Task.external_id == task_ext,
                                   Task.project_id == proj.id).first()
        assert t is not None
        assert t.type == "chore"
        assert t.origin_finding_id is not None
        assert t.name.startswith("Fix:")
        assert "Suggested action" in (t.description or "")
        # cleanup
        db.query(Task).filter(Task.id == t.id).delete()
        db.query(Finding).filter(Finding.external_id == ext,
                                 Finding.project_id == proj.id).delete()
        db.commit()
    finally:
        db.close()


def test_create_task_is_idempotent(ps):
    """Second call for the same finding returns the existing task, not a new one."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ext = _seed_finding(db, proj.id, title="Race condition in cache invalidation")
    finally:
        db.close()

    r1 = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/{ext}/create-task")
    assert r1.status_code == 200
    first_task = r1.json()["task_external_id"]
    assert r1.json()["created"] is True

    r2 = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/{ext}/create-task")
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["created"] is False
    assert j2["task_external_id"] == first_task

    # cleanup
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        db.query(Task).filter(Task.external_id == first_task,
                              Task.project_id == proj.id).delete()
        db.query(Finding).filter(Finding.external_id == ext,
                                 Finding.project_id == proj.id).delete()
        db.commit()
    finally:
        db.close()


def test_create_task_rejects_dismissed_finding(ps):
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ext = _seed_finding(db, proj.id, status="DISMISSED")
    finally:
        db.close()

    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/{ext}/create-task")
    assert r.status_code == 409
    assert "DISMISSED" in r.json()["detail"]

    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        db.query(Finding).filter(Finding.external_id == ext,
                                 Finding.project_id == proj.id).delete()
        db.commit()
    finally:
        db.close()


def test_create_task_404_for_missing_finding(ps):
    s, slug = ps
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/F-does-not-exist/create-task")
    assert r.status_code == 404


def test_task_report_exposes_origin_finding(ps):
    """When a task has origin_finding_id, the report API surfaces a chip."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ext = _seed_finding(db, proj.id,
                            title="Unbounded log retention — GDPR risk",
                            severity="MEDIUM")
    finally:
        db.close()

    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/{ext}/create-task")
    assert r.status_code == 200
    task_ext = r.json()["task_external_id"]

    rep = s.get(f"{BASE}/api/v1/projects/{slug}/tasks/{task_ext}/report")
    assert rep.status_code == 200
    of = rep.json().get("origin_finding")
    assert of is not None
    assert of["external_id"] == ext
    assert of["severity"] == "MEDIUM"
    assert "GDPR" in of["title"]

    # HTML chip
    h = s.get(f"{BASE}/ui/projects/{slug}/tasks/{task_ext}")
    assert h.status_code == 200
    assert "from finding" in h.text
    assert ext in h.text

    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        db.query(Task).filter(Task.external_id == task_ext,
                              Task.project_id == proj.id).delete()
        db.query(Finding).filter(Finding.external_id == ext,
                                 Finding.project_id == proj.id).delete()
        db.commit()
    finally:
        db.close()


def test_task_report_html_shows_finding_to_task_button(ps):
    """The task report page should render a `→ Task` button next to each finding."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        task_ext = task.external_id
    finally:
        db.close()
    r = s.get(f"{BASE}/ui/projects/{slug}/tasks/{task_ext}")
    assert r.status_code == 200
    # The fixture populates findings on tasks — just check the handler JS+CSRF plumbing
    # exists in the page. (Whether a specific task has findings varies.)
    assert "findingToTask(" in r.text
    assert "/findings/" in r.text
    assert "/create-task" in r.text
