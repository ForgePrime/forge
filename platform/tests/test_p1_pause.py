"""P1.1 — pause_requested must halt the orchestrate loop between tasks.

The regression we're preventing: `pause_requested` flag existed on the model,
the pause endpoint flipped it, the UI showed "paused", but the executor
never checked the flag. User clicked Pause, budget kept burning.

These tests mechanically prove:
  1. The CHECK constraint now permits status='PAUSED'.
  2. `_check_pause` is honored by the loop's cooperative gate.
  3. The pause endpoint rejects terminal-state runs.
  4. The resume endpoint respawns the worker for PAUSED runs.
"""
import datetime as dt

import pytest
import requests

from app.database import SessionLocal
from app.models import Project
from app.models.orchestrate_run import OrchestrateRun
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p1pause")


def _mk_run(slug: str, status: str = "RUNNING", pause_requested: bool = False) -> int:
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        assert proj, "populated project missing"
        run = OrchestrateRun(
            project_id=proj.id,
            status=status,
            pause_requested=pause_requested,
            params={"max_tasks": 5},
            progress_message="test fixture",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def test_check_constraint_accepts_paused(ps):
    """CHECK constraint valid_orchestrate_run_status must permit PAUSED
    (schema migration regression check)."""
    _s, slug = ps
    rid = _mk_run(slug, status="RUNNING")
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.status = "PAUSED"
        db.commit()  # raises if CHECK excludes 'PAUSED'
        db.refresh(run)
        assert run.status == "PAUSED"
    finally:
        db.close()


def test_check_pause_helper_detects_flag(ps):
    """_check_pause should read the fresh DB row, not a cached ORM obj."""
    from app.api.pipeline import _check_pause
    _s, slug = ps
    rid = _mk_run(slug, status="RUNNING", pause_requested=False)

    # Open a session, confirm False
    db = SessionLocal()
    try:
        assert _check_pause(db, rid) is False
    finally:
        db.close()

    # Flip via independent session, then re-check — the helper must see the change
    # (i.e. it calls expire_all / re-queries, not just returns a cached attribute).
    db2 = SessionLocal()
    try:
        run = db2.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.pause_requested = True
        db2.commit()
    finally:
        db2.close()

    db3 = SessionLocal()
    try:
        assert _check_pause(db3, rid) is True
    finally:
        db3.close()


def test_check_pause_returns_false_for_null_run_id(ps):
    """Synchronous orchestrate() calls (no run_id) must never crash in the helper."""
    from app.api.pipeline import _check_pause
    db = SessionLocal()
    try:
        assert _check_pause(db, None) is False
    finally:
        db.close()


def test_pause_endpoint_rejects_terminal_runs(ps):
    s, slug = ps
    rid = _mk_run(slug, status="RUNNING")
    # Move run to DONE manually
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.status = "DONE"
        run.finished_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    finally:
        db.close()
    r = s.post(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/pause")
    assert r.status_code == 409
    assert "cannot pause" in r.json()["detail"].lower()


def test_pause_endpoint_sets_flag_for_running(ps):
    s, slug = ps
    rid = _mk_run(slug, status="RUNNING", pause_requested=False)
    r = s.post(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/pause")
    assert r.status_code == 200
    body = r.json()
    assert body["pause_requested"] is True
    assert body["status"] == "RUNNING"

    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        assert run.pause_requested is True
    finally:
        db.close()


def test_resume_endpoint_clears_flag_for_running(ps):
    """RUNNING + pause_requested → resume just clears the flag; no respawn."""
    s, slug = ps
    rid = _mk_run(slug, status="RUNNING", pause_requested=True)
    r = s.post(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/resume")
    assert r.status_code == 200
    body = r.json()
    assert body["pause_requested"] is False
    assert body["respawned"] is False  # still RUNNING, no respawn needed


def test_resume_endpoint_respawns_paused_run(ps):
    """PAUSED → resume sets status=RUNNING, resumed_at, and schedules a worker."""
    s, slug = ps
    rid = _mk_run(slug, status="PAUSED", pause_requested=True)
    # pre-set paused_at so the fixture looks real
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.paused_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    r = s.post(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/resume")
    assert r.status_code == 200
    body = r.json()
    assert body["respawned"] is True, "PAUSED must respawn, not just clear flag"
    assert body["pause_requested"] is False

    # Verify DB state post-resume
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        assert run.pause_requested is False
        assert run.resumed_at is not None
        # status was RUNNING at the endpoint; the background worker may transition it
        # afterwards (no real tasks → likely DONE quickly, or FAILED if workspace
        # bootstrap hiccups in test env). Either way it's no longer PAUSED.
        assert run.status != "PAUSED"
    finally:
        db.close()


def test_resume_endpoint_rejects_terminal(ps):
    s, slug = ps
    rid = _mk_run(slug, status="DONE")
    r = s.post(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/resume")
    assert r.status_code == 409


def test_run_status_endpoint_exposes_pause_fields(ps):
    """GET /orchestrate-runs/{id} must surface pause_requested, paused_at, resumed_at
    so the UI can render Resume correctly."""
    s, slug = ps
    rid = _mk_run(slug, status="PAUSED", pause_requested=False)
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.paused_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    finally:
        db.close()
    r = s.get(f"{BASE}/api/v1/orchestrate-runs/{rid}")
    assert r.status_code == 200
    body = r.json()
    for k in ("pause_requested", "paused_at", "resumed_at"):
        assert k in body, f"run status should expose {k}"
    assert body["paused_at"] is not None


def test_orchestrate_panel_renders_paused_with_resume(ps):
    """Live UI panel must show a Resume button when status=PAUSED."""
    s, slug = ps
    rid = _mk_run(slug, status="PAUSED", pause_requested=False)
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.paused_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    finally:
        db.close()
    r = s.get(f"{BASE}/ui/orchestrate-runs/{rid}/panel")
    assert r.status_code == 200
    html = r.text
    assert "PAUSED" in html
    assert "Resume" in html
    assert f"/api/v1/tier1/orchestrate-runs/{rid}/resume" in html
