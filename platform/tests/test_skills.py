"""F1+F2+F5 skills v0 — non-happy-path tests."""
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
        "email": f"sk-{TS}@t.com", "password": "pw-test-12345", "full_name": "SK",
        "org_slug": f"sk-{TS}", "org_name": "SK",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"sk-{TS}"
    s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": "SK", "goal": "x"},
           allow_redirects=False)
    return s, slug


def test_t1_skills_anon():
    r = requests.get(f"{BASE}/api/v1/skills")
    assert r.status_code in (401, 403)


def test_t2_seed_built_ins(session_and_slug):
    """First call must seed built-in skills idempotently."""
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/skills")
    assert r.status_code == 200
    body = r.json()
    ids = {sk["external_id"] for sk in body["skills"]}
    for required in ("SK-security-owasp", "SK-scenario-gen-nonhappy",
                     "MS-pytest-parametrize", "OP-best-dev-django", "OP-hipaa-auditor",
                     "SK-cite-src-enforcer"):
        assert required in ids, f"built-in {required} missing"


def test_t3_idempotent_seed(session_and_slug):
    """Second call must NOT duplicate built-ins."""
    s, _ = session_and_slug
    r1 = s.get(f"{BASE}/api/v1/skills")
    n1 = len(r1.json()["skills"])
    r2 = s.get(f"{BASE}/api/v1/skills")
    n2 = len(r2.json()["skills"])
    assert n1 == n2, "seeding is not idempotent"


def test_t4_filter_by_category(session_and_slug):
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/skills?category=OPINION")
    assert r.status_code == 200
    cats = {sk["category"] for sk in r.json()["skills"]}
    assert cats == {"OPINION"} or cats == set(), f"got mixed cats: {cats}"


def test_t5_filter_by_phase(session_and_slug):
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/skills?phase=challenger")
    assert r.status_code == 200
    for sk in r.json()["skills"]:
        assert "challenger" in sk["applies_to_phases"]


def test_t6_attach_unknown_skill_404(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/skills/projects/{slug}/attach",
               json={"skill_external_id": "SK-nonexistent-xyz"})
    assert r.status_code == 404


def test_t7_attach_invalid_mode_422(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/skills/projects/{slug}/attach",
               json={"skill_external_id": "SK-security-owasp", "attach_mode": "wrongmode"})
    assert r.status_code == 422


def test_t8_attach_then_list_then_detach(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/skills/projects/{slug}/attach",
               json={"skill_external_id": "SK-security-owasp", "attach_mode": "auto"})
    assert r.status_code == 200
    r = s.get(f"{BASE}/api/v1/skills/projects/{slug}")
    assert r.status_code == 200
    ids = [a["external_id"] for a in r.json()["attached"]]
    assert "SK-security-owasp" in ids

    r = s.delete(f"{BASE}/api/v1/skills/projects/{slug}/attach/SK-security-owasp")
    assert r.status_code == 200
    r = s.get(f"{BASE}/api/v1/skills/projects/{slug}")
    ids = [a["external_id"] for a in r.json()["attached"]]
    assert "SK-security-owasp" not in ids


def test_t9_skills_tab_renders(session_and_slug):
    s, slug = session_and_slug
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=skills")
    assert r.status_code == 200
    assert "Skills library" in r.text
    assert "skills-attached" in r.text and "skills-catalog" in r.text


def test_t10_attach_to_foreign_project(session_and_slug):
    s, _ = session_and_slug
    r = s.post(f"{BASE}/api/v1/skills/projects/totally-fake-zzz/attach",
               json={"skill_external_id": "SK-security-owasp"})
    assert r.status_code == 404
