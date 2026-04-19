"""Chunks AC+AD+AE+AF — non-happy-path tests for:
- Objective DAG dependencies (add/remove/cycle/self)
- Post-stage hooks CRUD
- Decision resolve
- KB conflicts endpoint
- Objective rollup
- Docs markdown export
- SSE stream endpoint (connect + headers, no full consume)
"""
import os
import time
import pytest
import requests

BASE = os.environ.get("FORGE_TEST_BASE", "http://127.0.0.1:8063")
TS = int(time.time())


@pytest.fixture(scope="module")
def s_slug():
    s = requests.Session()
    r = s.post(f"{BASE}/ui/signup", data={
        "email": f"acaf-{TS}@t.com", "password": "pw-test-12345", "full_name": "ACAF",
        "org_slug": f"acaf-{TS}", "org_name": "ACAF",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"acaf-{TS}"
    s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": "ACAF", "goal": "x"},
           allow_redirects=False)
    return s, slug


# -------------------- Objective DAG dependencies --------------------

def test_dag_self_dependency_422(s_slug):
    from app.database import SessionLocal
    from app.models import Project, Objective
    s, slug = s_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        db.add(Objective(project_id=proj.id, external_id="O-AC1",
                         title="dag test 1", business_context="x" * 20,
                         status="ACTIVE", priority=3))
        db.commit()
    finally:
        db.close()
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-AC1/dependencies",
               json={"depends_on_external_id": "O-AC1"})
    assert r.status_code == 422


def test_dag_cycle_rejected(s_slug):
    from app.database import SessionLocal
    from app.models import Project, Objective
    s, slug = s_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        for ext in ("O-AC2", "O-AC3"):
            db.add(Objective(project_id=proj.id, external_id=ext,
                             title=ext, business_context="x" * 20,
                             status="ACTIVE", priority=3))
        db.commit()
    finally:
        db.close()
    # AC2 → AC3
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-AC2/dependencies",
               json={"depends_on_external_id": "O-AC3"})
    assert r.status_code == 200
    # AC3 → AC2 = cycle
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-AC3/dependencies",
               json={"depends_on_external_id": "O-AC2"})
    assert r.status_code == 409
    assert "cycle" in r.json()["detail"].lower()


def test_dag_get_shape(s_slug):
    s, slug = s_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/objectives-dag")
    assert r.status_code == 200
    body = r.json()
    assert "nodes" in body and "edges" in body


# -------------------- Post-stage hooks --------------------

def test_hook_list_empty(s_slug):
    s, slug = s_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/hooks")
    assert r.status_code == 200
    assert r.json()["hooks"] == []


def test_hook_invalid_stage_422(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/hooks",
               json={"stage": "before_creation_of_universe"})
    assert r.status_code == 422


def test_hook_create_and_delete(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/hooks",
               json={"stage": "after_analysis",
                     "skill_external_id": "SK-cite-src-enforcer",
                     "purpose_text": "enforce citations post-analysis"})
    assert r.status_code == 200, r.text
    hid = r.json()["id"]
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/hooks")
    assert any(h["id"] == hid for h in r.json()["hooks"])
    r = s.delete(f"{BASE}/api/v1/tier1/projects/{slug}/hooks/{hid}")
    assert r.status_code == 200


def test_hook_with_unknown_skill_404(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/hooks",
               json={"stage": "after_develop",
                     "skill_external_id": "SK-does-not-exist"})
    assert r.status_code == 404


# -------------------- Decision resolve --------------------

def test_resolve_nonexistent_decision_404(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/decisions/D-9999/resolve",
               json={"recommendation": "does not matter"})
    assert r.status_code == 404


def test_resolve_short_recommendation_422(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/decisions/D-ANY/resolve",
               json={"recommendation": "no"})
    assert r.status_code == 422


# -------------------- KB conflicts --------------------

def test_kb_conflicts_empty_project(s_slug):
    s, slug = s_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/kb/conflicts")
    assert r.status_code == 200
    body = r.json()
    assert body["conflicts"] == []


def test_kb_conflicts_detection(s_slug):
    s, slug = s_slug
    s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/note", json={
        "title": "Manifesto", "content": "We must be on-prem, no compromises."})
    s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/note", json={
        "title": "Exec deck", "content": "Move everything to AWS cloud."})
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/kb/conflicts")
    body = r.json()
    # At least one pair should be detected (on-prem vs aws/cloud)
    assert len(body["conflicts"]) >= 1


# -------------------- Objective rollup --------------------

def test_rollup_empty_project_returns_empty(s_slug):
    s, slug = s_slug
    # may have objectives from earlier tests
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/docs/objective-rollup")
    assert r.status_code == 200
    assert "rollups" in r.json()


def test_docs_export_md_downloads(s_slug):
    s, slug = s_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/docs/export.md")
    assert r.status_code == 200
    # Should be markdown
    ct = r.headers.get("content-type", "")
    assert "text/markdown" in ct or "text/plain" in ct
    # Should contain a Per-objective rollup section when there are objectives
    assert "# " in r.text or "## " in r.text


# -------------------- SSE stream --------------------

def test_sse_stream_nonexistent_run_404(s_slug):
    s, _ = s_slug
    # stream endpoint expects to verify scope before streaming
    r = s.get(f"{BASE}/api/v1/tier1/orchestrate-runs/99999999/stream",
              stream=True, timeout=3)
    assert r.status_code == 404


def test_sse_stream_on_existing_run_sets_event_stream_header(s_slug):
    from app.database import SessionLocal
    from app.models import Project
    from app.models.orchestrate_run import OrchestrateRun
    s, slug = s_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        run = OrchestrateRun(project_id=proj.id, status="DONE",
                             params={"max_tasks": 1}, tasks_completed=1,
                             tasks_failed=0, total_cost_usd=0.1)
        db.add(run); db.commit(); rid = run.id
    finally:
        db.close()
    r = s.get(f"{BASE}/api/v1/tier1/orchestrate-runs/{rid}/stream",
              stream=True, timeout=5)
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    # Read at least one event chunk then close (don't block on 30-min cap)
    chunks = r.iter_lines(decode_unicode=True)
    saw_state = False
    for _ in range(20):
        try:
            line = next(chunks)
            if line.startswith("event:"):
                saw_state = True
                break
        except StopIteration:
            break
    r.close()
    assert saw_state, "expected at least one SSE event"
