"""P5.7 extension — graceful shutdown helpers.

The orphan-recovery module grew two more helpers that fire on lifespan shutdown:
  - release_in_progress_tasks: flips stuck IN_PROGRESS tasks back to TODO
  - mark_running_runs_interrupted_on_shutdown: no staleness filter; every
    RUNNING/PAUSED/PENDING run becomes INTERRUPTED because the worker is dying

CRITICAL: tests MUST pass `project_id` to these helpers — otherwise they touch
all projects' active state, including in-flight live runs from another session.
This was learned the hard way during P5.4 round-2c when an unscoped test call
stomped on a real Phase-C orchestrate run."""
import datetime as dt

import pytest

from app.database import SessionLocal
from app.models import Execution, Project, Task
from app.models.orchestrate_run import OrchestrateRun
from app.services.orphan_recovery import (
    mark_running_runs_interrupted_on_shutdown,
    release_in_progress_tasks,
)
from tests.conftest_populated import build_populated_project


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p5shut")


def _project_id(slug: str) -> int:
    db = SessionLocal()
    try:
        return db.query(Project).filter(Project.slug == slug).first().id
    finally:
        db.close()


def _seed_run(slug: str, status: str) -> int:
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        run = OrchestrateRun(project_id=proj.id, status=status, params={"max_tasks": 1})
        db.add(run); db.commit(); db.refresh(run)
        return run.id
    finally:
        db.close()


def _set_task_in_progress(proj_id: int, ext: str) -> int:
    db = SessionLocal()
    try:
        t = db.query(Task).filter(
            Task.project_id == proj_id, Task.external_id == ext
        ).first()
        if not t:
            return -1
        t.status = "IN_PROGRESS"
        t.started_at = dt.datetime.now(dt.timezone.utc)
        t.agent = "test"
        db.commit()
        return t.id
    finally:
        db.close()


# ---- release_in_progress_tasks --------------------------------------

def test_release_in_progress_flips_to_todo(ps):
    _s, slug = ps
    pid = _project_id(slug)
    tid = _set_task_in_progress(pid, "T-001")
    if tid == -1:
        pytest.skip("populated fixture lacks T-001 — this test assumes it")
    db = SessionLocal()
    try:
        released = release_in_progress_tasks(db, project_id=pid)
    finally:
        db.close()
    assert tid in released
    db = SessionLocal()
    try:
        t = db.query(Task).filter(Task.id == tid).first()
        assert t.status == "TODO"
        assert t.started_at is None
        assert t.agent is None
    finally:
        db.close()


def test_release_is_idempotent(ps):
    """Running twice returns an empty list the second time."""
    _s, slug = ps
    pid = _project_id(slug)
    db = SessionLocal()
    try:
        first = release_in_progress_tasks(db, project_id=pid)
        second = release_in_progress_tasks(db, project_id=pid)
    finally:
        db.close()
    assert second == []  # no IN_PROGRESS left after first call


def test_release_ignores_other_statuses(ps):
    """DONE, TODO, FAILED — untouched."""
    _s, slug = ps
    pid = _project_id(slug)
    db = SessionLocal()
    try:
        statuses_before = {
            t.id: t.status for t in db.query(Task).filter(
                Task.project_id == pid, Task.status != "IN_PROGRESS"
            ).all()
        }
    finally:
        db.close()

    db = SessionLocal()
    try:
        release_in_progress_tasks(db, project_id=pid)
    finally:
        db.close()

    db = SessionLocal()
    try:
        for tid, prev in statuses_before.items():
            cur = db.query(Task).filter(Task.id == tid).first()
            if cur:
                assert cur.status == prev, f"Task {tid} was touched: {prev} -> {cur.status}"
    finally:
        db.close()


def test_release_scoped_does_not_touch_other_projects(ps):
    """Critical: passing project_id to release MUST NOT touch tasks in other projects."""
    _s, slug = ps
    pid = _project_id(slug)
    # Set up: an IN_PROGRESS task in our test project + a synthetic IN_PROGRESS
    # task in a different project (we'll just use the populated fixture itself for that
    # other project — but we need a separate project. So mock it by creating one inline.)
    db = SessionLocal()
    other_proj_id = None
    other_task_id = None
    try:
        from app.models import Organization
        org = db.query(Organization).first()
        other_proj = Project(slug=f"other-{int(dt.datetime.now().timestamp())}",
                             name="other", organization_id=org.id if org else None)
        db.add(other_proj); db.commit(); db.refresh(other_proj)
        other_proj_id = other_proj.id
        other_task = Task(
            project_id=other_proj_id, external_id="T-OTHER", name="other-task",
            description="for the scope test", instruction="x",
            type="feature", status="IN_PROGRESS",
            started_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(other_task); db.commit(); db.refresh(other_task)
        other_task_id = other_task.id
    finally:
        db.close()

    # Now release ONLY for our test project
    db = SessionLocal()
    try:
        released = release_in_progress_tasks(db, project_id=pid)
    finally:
        db.close()

    # Other project's task must STILL be IN_PROGRESS
    db = SessionLocal()
    try:
        ot = db.query(Task).filter(Task.id == other_task_id).first()
        assert ot.status == "IN_PROGRESS", "scope leak: another project's task got released"
        assert other_task_id not in released
    finally:
        db.close()

    # Cleanup
    db = SessionLocal()
    try:
        db.query(Task).filter(Task.id == other_task_id).delete()
        db.query(Project).filter(Project.id == other_proj_id).delete()
        db.commit()
    finally:
        db.close()


# ---- mark_running_runs_interrupted_on_shutdown -------------------

def test_shutdown_flips_running_to_interrupted(ps):
    _s, slug = ps
    pid = _project_id(slug)
    rid = _seed_run(slug, "RUNNING")
    db = SessionLocal()
    try:
        touched = mark_running_runs_interrupted_on_shutdown(db, project_id=pid)
    finally:
        db.close()
    assert rid in touched
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        assert run.status == "INTERRUPTED"
        assert run.error and "Graceful shutdown" in run.error
        assert run.finished_at is not None
    finally:
        db.close()


def test_shutdown_flips_paused_too(ps):
    _s, slug = ps
    pid = _project_id(slug)
    rid = _seed_run(slug, "PAUSED")
    db = SessionLocal()
    try:
        touched = mark_running_runs_interrupted_on_shutdown(db, project_id=pid)
    finally:
        db.close()
    assert rid in touched


def test_shutdown_ignores_terminal(ps):
    """DONE, FAILED, CANCELLED, PARTIAL_FAIL untouched."""
    _s, slug = ps
    pid = _project_id(slug)
    terminal_ids = [_seed_run(slug, s) for s in
                    ("DONE", "FAILED", "CANCELLED", "PARTIAL_FAIL", "BUDGET_EXCEEDED",
                     "INTERRUPTED")]
    db = SessionLocal()
    try:
        touched = mark_running_runs_interrupted_on_shutdown(db, project_id=pid)
    finally:
        db.close()
    for rid in terminal_ids:
        assert rid not in touched


def test_shutdown_preserves_existing_error(ps):
    """User-set error should be appended to, not overwritten."""
    _s, slug = ps
    pid = _project_id(slug)
    rid = _seed_run(slug, "RUNNING")
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.error = "prior manual note"
        db.commit()
    finally:
        db.close()
    db = SessionLocal()
    try:
        mark_running_runs_interrupted_on_shutdown(db, project_id=pid)
    finally:
        db.close()
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        assert "prior manual note" in (run.error or "")
        assert "Graceful shutdown" in (run.error or "")
    finally:
        db.close()


def test_shutdown_no_staleness_filter(ps):
    """Unlike startup recovery, shutdown takes everything active — even freshly-updated."""
    _s, slug = ps
    pid = _project_id(slug)
    rid = _seed_run(slug, "RUNNING")
    db = SessionLocal()
    try:
        db.execute(
            OrchestrateRun.__table__.update()
            .where(OrchestrateRun.id == rid)
            .values(updated_at=dt.datetime.now(dt.timezone.utc))
        )
        db.commit()
    finally:
        db.close()
    db = SessionLocal()
    try:
        touched = mark_running_runs_interrupted_on_shutdown(db, project_id=pid)
    finally:
        db.close()
    assert rid in touched


def test_shutdown_scoped_does_not_touch_other_projects(ps):
    """Critical: passing project_id MUST scope correctly. Production calls without it
    so EVERY active run dies on shutdown (correct), but tests must scope down."""
    _s, slug = ps
    pid = _project_id(slug)
    db = SessionLocal()
    other_proj_id = None
    other_run_id = None
    try:
        from app.models import Organization
        org = db.query(Organization).first()
        other_proj = Project(slug=f"shut-other-{int(dt.datetime.now().timestamp())}",
                             name="other", organization_id=org.id if org else None)
        db.add(other_proj); db.commit(); db.refresh(other_proj)
        other_proj_id = other_proj.id
        other_run = OrchestrateRun(project_id=other_proj_id, status="RUNNING",
                                    params={"max_tasks": 1})
        db.add(other_run); db.commit(); db.refresh(other_run)
        other_run_id = other_run.id
    finally:
        db.close()

    db = SessionLocal()
    try:
        touched = mark_running_runs_interrupted_on_shutdown(db, project_id=pid)
    finally:
        db.close()

    # Other project's run must STILL be RUNNING
    db = SessionLocal()
    try:
        or_run = db.query(OrchestrateRun).filter(OrchestrateRun.id == other_run_id).first()
        assert or_run.status == "RUNNING", "scope leak: another project's run got marked INTERRUPTED"
        assert other_run_id not in touched
    finally:
        db.close()

    # Cleanup
    db = SessionLocal()
    try:
        db.query(OrchestrateRun).filter(OrchestrateRun.id == other_run_id).delete()
        db.query(Project).filter(Project.id == other_proj_id).delete()
        db.commit()
    finally:
        db.close()
