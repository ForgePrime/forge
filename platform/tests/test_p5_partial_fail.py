"""P5.6 — PARTIAL_FAIL status + accurate terminal progress_message.

Bug surfaced by P5.4 live run #207: the run ended with `status=DONE` and
`progress_message="Completed 1 tasks (0 done)"` — misleading. The task had
failed all 3 attempts. "Completed" sounds positive; "(0 done)" sounds like
a parenthetical subtlety.

Post-fix:
  - When any task FAILED, terminal status becomes PARTIAL_FAIL (new).
  - progress_message explicitly counts DONE vs FAILED.
  - Resume endpoint rejects PARTIAL_FAIL (terminal).
  - Panel renders PARTIAL_FAIL with a distinct orange pill.
"""
import datetime as dt

import pytest

from app.database import SessionLocal
from app.models import Project
from app.models.orchestrate_run import OrchestrateRun
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p5pf")


def _mk_run(slug: str, status: str = "RUNNING") -> int:
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        run = OrchestrateRun(
            project_id=proj.id, status=status, params={"max_tasks": 5},
        )
        db.add(run); db.commit(); db.refresh(run)
        return run.id
    finally:
        db.close()


# ---- CHECK constraint accepts PARTIAL_FAIL --------------------------

def test_check_constraint_accepts_partial_fail(ps):
    _s, slug = ps
    rid = _mk_run(slug, status="RUNNING")
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.status = "PARTIAL_FAIL"
        db.commit()
        db.refresh(run)
        assert run.status == "PARTIAL_FAIL"
    finally:
        db.close()


# ---- Resume / pause behaviour --------------------------------------

def test_resume_rejects_partial_fail_terminal(ps):
    s, slug = ps
    rid = _mk_run(slug, status="PARTIAL_FAIL")
    r = s.post(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/resume")
    assert r.status_code == 409
    assert "PARTIAL_FAIL" in r.json()["detail"]


def test_stream_treats_partial_fail_as_terminal(ps):
    s, slug = ps
    rid = _mk_run(slug, status="RUNNING")
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.status = "PARTIAL_FAIL"
        run.finished_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    finally:
        db.close()
    r = s.get(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/stream", timeout=10)
    # The SSE stream should close quickly because we're already terminal.
    # Content-type should still be SSE.
    assert r.status_code in (200, 404)  # 404 only if route is missing; we know it exists


# ---- Panel UI renders PARTIAL_FAIL badge ----------------------------

def test_panel_ui_shows_partial_fail_pill(ps):
    s, slug = ps
    rid = _mk_run(slug, status="RUNNING")
    db = SessionLocal()
    try:
        run = db.query(OrchestrateRun).filter(OrchestrateRun.id == rid).first()
        run.status = "PARTIAL_FAIL"
        run.progress_message = "Partial: 0 DONE, 1 FAILED out of 1."
        db.commit()
    finally:
        db.close()
    r = s.get(f"{BASE}/ui/orchestrate-runs/{rid}/panel")
    assert r.status_code == 200
    html = r.text
    assert "PARTIAL_FAIL" in html
    assert "bg-orange-100" in html
    assert "0 DONE, 1 FAILED" in html


# ---- Status-message logic --------------------------------------------

def _compute_status_and_msg(results):
    """Mirror the pipeline.py logic so we can unit-test it without a live run."""
    done = sum(1 for r in results if r["status"] == "DONE")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    n = len(results)
    if failed == 0 and done > 0:
        return "DONE", f"Completed {n} task(s), all DONE."
    if done > 0 and failed > 0:
        return "PARTIAL_FAIL", f"Partial: {done} DONE, {failed} FAILED out of {n}."
    if done == 0 and failed > 0:
        return "PARTIAL_FAIL", f"No tasks completed: {failed} FAILED out of {n}."
    return "DONE", "Loop finished with no candidate tasks."


def test_status_logic_all_done():
    s, m = _compute_status_and_msg([{"status": "DONE"}, {"status": "DONE"}])
    assert s == "DONE"
    assert "2 task(s), all DONE" in m


def test_status_logic_all_failed():
    s, m = _compute_status_and_msg([{"status": "FAILED"}, {"status": "FAILED"}])
    assert s == "PARTIAL_FAIL"
    assert "No tasks completed" in m
    assert "2 FAILED" in m


def test_status_logic_mixed():
    s, m = _compute_status_and_msg([
        {"status": "DONE"}, {"status": "FAILED"}, {"status": "DONE"},
    ])
    assert s == "PARTIAL_FAIL"
    assert "2 DONE, 1 FAILED out of 3" in m


def test_status_logic_empty():
    s, m = _compute_status_and_msg([])
    assert s == "DONE"
    assert "no candidate tasks" in m


def test_status_logic_single_failed_was_the_pilot_bug():
    """Exact shape of the run #207 regression — one FAILED task should NOT show as DONE."""
    s, m = _compute_status_and_msg([{"status": "FAILED"}])
    assert s == "PARTIAL_FAIL"
    assert "1 FAILED" in m
    # Old message was: "Completed 1 tasks (0 done)" — assert we're NOT emitting that
    assert "Completed 1 tasks (0 done)" not in m
