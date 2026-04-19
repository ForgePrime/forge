"""Objective detail — mockup 09 alignment tests (non-happy-path)."""
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
        "email": f"od-{TS}@t.com", "password": "pw-test-12345", "full_name": "OD",
        "org_slug": f"od-{TS}", "org_name": "OD",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"od-{TS}"
    s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": "OD", "goal": "x"},
           allow_redirects=False)
    # Create an objective directly
    from app.database import SessionLocal
    from app.models import Project, Objective
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        o = Objective(project_id=proj.id, external_id="O-001",
                      title="Test objective", business_context="x" * 30,
                      status="ACTIVE", priority=3)
        db.add(o); db.commit()
    finally:
        db.close()
    return s, slug


def test_objective_patch_description(s_slug):
    s, slug = s_slug
    r = s.patch(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001",
                json={"business_context": "Updated description with detail."})
    assert r.status_code == 200
    # Verify on the detail page
    r = s.get(f"{BASE}/ui/projects/{slug}/objectives/O-001")
    assert r.status_code == 200
    assert "Updated description with detail." in r.text


def test_scenario_add_short_label_rejected(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/scenarios",
               json={"label": "x", "kind": "edge_case"})
    assert r.status_code == 422


def test_scenario_invalid_kind_rejected(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/scenarios",
               json={"label": "valid label", "kind": "banana"})
    assert r.status_code == 422


def test_scenario_add_then_delete(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/scenarios",
               json={"label": "NULL row during migration", "kind": "edge_case",
                     "description": "Skip + audit"})
    assert r.status_code == 200
    sid = r.json()["scenario_id"]
    # Add another
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/scenarios",
               json={"label": "Auth outage mid-migration", "kind": "failure_mode"})
    assert r.status_code == 200
    # Delete first
    r = s.delete(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/scenarios/{sid}")
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_challenger_check_round_trip(s_slug):
    s, slug = s_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/challenger-checks",
               json={"text": "Plan handles every scenario above."})
    assert r.status_code == 200
    cid = r.json()["check_id"]
    r = s.delete(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/challenger-checks/{cid}")
    assert r.status_code == 200


def test_activity_returns_shape(s_slug):
    s, slug = s_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/activity")
    assert r.status_code == 200
    assert "events" in r.json()


def test_objective_detail_page_shows_new_sections(s_slug):
    s, slug = s_slug
    # seed scenario + check so sections are rendered
    s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/scenarios",
           json={"label": "SECURITY scenario check", "kind": "security"})
    s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/challenger-checks",
           json={"text": "No implicit cloud dependency introduced"})
    r = s.get(f"{BASE}/ui/projects/{slug}/objectives/O-001")
    assert r.status_code == 200
    html = r.text
    # Mockup-09 sections must all be present:
    for needle in ("Test scenarios", "Challenger will verify", "Scrutiny debt",
                   "Recent activity", "Ask Forge to", "DAG neighbors"):
        assert needle in html, f"missing section '{needle}'"
    # Scenario and check we added must render
    assert "SECURITY scenario check" in html
    assert "No implicit cloud dependency introduced" in html
