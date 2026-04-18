"""Tier-2 forensics — J1 cost-drill + J2 forecast non-happy-path tests."""
import os
import time
import pytest
import requests

BASE = os.environ.get("FORGE_TEST_BASE", "http://127.0.0.1:8063")
TS = int(time.time())


@pytest.fixture(scope="module")
def session_and_slug():
    s = requests.Session()
    r = s.post(f"{BASE}/ui/signup", data={
        "email": f"t2-{TS}@t.com", "password": "pw-test-12345", "full_name": "T2",
        "org_slug": f"t2-{TS}", "org_name": "T2",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"t2-{TS}"
    s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": "T2", "goal": "x"},
           allow_redirects=False)
    return s, slug


def test_t1_cost_forensic_anon():
    r = requests.get(f"{BASE}/api/v1/tier1/projects/x/tasks/T-1/cost-forensic")
    assert r.status_code in (401, 403)


def test_t2_cost_forensic_nonexistent_task(session_and_slug):
    s, slug = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/T-9999/cost-forensic")
    assert r.status_code == 404


def test_t3_cost_forensic_task_with_no_executions(session_and_slug):
    """NOT happy: task exists but never ran. Should still return shape with zeros."""
    from app.database import SessionLocal
    from app.models import Project, Task
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        t = Task(project_id=proj.id, external_id="T-T3", name="never-ran",
                 instruction="x" * 30, type="develop", status="TODO")
        db.add(t); db.commit()
    finally:
        db.close()
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/T-T3/cost-forensic")
    assert r.status_code == 200
    body = r.json()
    assert body["total_cost_usd"] == 0
    assert body["calls_count"] == 0
    assert body["executions_count"] == 0
    assert "no significant context growth" in body["root_cause_hint"].lower()


def test_t4_forecast_nonexistent_run():
    r = requests.get(f"{BASE}/api/v1/tier1/orchestrate-runs/9999999/forecast")
    assert r.status_code in (401, 403, 404)


def test_t5_forecast_zero_completed_returns_zero_avg(session_and_slug):
    """NOT happy: just-started run has no completed tasks → avg should be 0, projected = spent."""
    from app.database import SessionLocal
    from app.models import Project
    from app.models.orchestrate_run import OrchestrateRun
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        run = OrchestrateRun(project_id=proj.id, status="RUNNING",
                             params={"max_tasks": 5},
                             tasks_completed=0, tasks_failed=0,
                             total_cost_usd=0.0)
        db.add(run); db.commit(); rid = run.id
    finally:
        db.close()
    r = s.get(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/forecast")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["spent_usd"] == 0
    assert body["avg_per_task_usd"] == 0
    assert body["projected_total_usd"] == 0
    assert body["over_budget_projected"] is False


def test_t6_forecast_warns_when_over_budget(session_and_slug):
    """NOT happy: half-done run already on track to bust the cap → warning fires."""
    from app.database import SessionLocal
    from app.models import Project
    from app.models.orchestrate_run import OrchestrateRun
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        # set per-run cap to $1 in project.config
        proj.config = {**(proj.config or {}), "budget_usd_per_run": 1.0}
        run = OrchestrateRun(project_id=proj.id, status="RUNNING",
                             params={"max_tasks": 10},
                             tasks_completed=2, tasks_failed=0,
                             total_cost_usd=0.40)  # avg 0.20/task * 8 left = $1.60 + 0.40 = $2.00 > $1 cap
        db.add(run); db.commit(); rid = run.id
    finally:
        db.close()
    r = s.get(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/forecast")
    assert r.status_code == 200
    body = r.json()
    assert body["over_budget_projected"] is True
    assert body["warning"] and "exceed" in body["warning"]
