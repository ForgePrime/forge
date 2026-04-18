"""Tier 3 + Tier 4 non-happy-path coverage:
E1 crafted mode toggle · I1-I5 autonomy · C4 URL crawler · C5 folder scanner
· J6 replay · F3 skill ROI · F4 marketplace promotion · K1-K3 org views
· L4 share-link business view."""
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
        "email": f"t34-{TS}@t.com", "password": "pw-test-12345", "full_name": "T34",
        "org_slug": f"t34-{TS}", "org_name": "T34",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"t34-{TS}"
    s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": "T34", "goal": "tier 3+4"},
           allow_redirects=False)
    return s, slug


# -------------------- E1 crafted mode --------------------

def test_exec_mode_default_direct(session_and_slug):
    s, slug = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/execution-mode")
    assert r.status_code == 200
    assert r.json()["execution_mode"] == "direct"


def test_exec_mode_toggle_to_crafted(session_and_slug):
    s, slug = session_and_slug
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/execution-mode",
              json={"execution_mode": "crafted"})
    assert r.status_code == 200
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/execution-mode")
    assert r.json()["execution_mode"] == "crafted"


def test_exec_mode_invalid_422(session_and_slug):
    s, slug = session_and_slug
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/execution-mode",
              json={"execution_mode": "magic"})
    assert r.status_code == 422


# -------------------- I1-I5 autonomy --------------------

def test_autonomy_fresh_project_starts_at_L1(session_and_slug):
    s, slug = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/autonomy")
    assert r.status_code == 200
    body = r.json()
    assert body["current_level"] == "L1"
    # Next = L2, eligible even without runs (L2 has 0-run threshold)
    assert body["next"]["level"] == "L2"
    assert body["next"]["eligible"] is True


def test_autonomy_cannot_skip_levels(session_and_slug):
    s, slug = session_and_slug
    # Fresh project (L1) → try to jump to L3 without first going L2
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/autonomy/promote",
               json={"target": "L3"})
    assert r.status_code == 409
    assert "cannot skip" in r.json()["detail"].lower()


def test_autonomy_promote_then_blocked(session_and_slug):
    s, slug = session_and_slug
    # L1 → L2 ok (no runs required)
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/autonomy/promote",
               json={"target": "L2"})
    assert r.status_code == 200
    # L2 → L3 requires 3 clean runs + 200-char contract
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/autonomy/promote",
               json={"target": "L3"})
    assert r.status_code == 409
    body_msg = r.json()["detail"]
    assert "clean orchestrate runs" in body_msg or "contract too short" in body_msg


def test_autonomy_invalid_level_422(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/autonomy/promote",
               json={"target": "L99"})
    assert r.status_code == 422


def test_objective_optout_round_trip(session_and_slug):
    from app.database import SessionLocal
    from app.models import Project, Objective
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        obj = Objective(project_id=proj.id, external_id="O-OPT",
                        title="opt out test", business_context="x" * 30,
                        status="ACTIVE", priority=3)
        db.add(obj); db.commit()
    finally:
        db.close()
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-OPT/autonomy-optout",
              json={"autonomy_optout": True})
    assert r.status_code == 200
    assert r.json()["autonomy_optout"] is True


# -------------------- C4 URL crawler --------------------

def test_url_crawl_httpbin(session_and_slug):
    """NOT happy: external network dep. If network is off, this should fail gracefully (not crash)."""
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/url", json={
        "title": "httpbin test",
        "target_url": "https://httpbin.org/html",
        "description": "public test fixture",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    # Either crawl succeeded (200 status) or failed with a warning — must NOT be server 500
    assert body["external_id"].startswith("SRC-")


def test_url_crawl_malformed_url_graceful(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/url", json={
        "title": "bad",
        "target_url": "not-a-real-url",
    })
    # httpx raises → service catches → 200 with warning, NOT 500
    assert r.status_code == 200
    assert r.json().get("warning")


# -------------------- C5 folder scanner --------------------

def test_folder_scan_nonexistent_path(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/folder", json={
        "title": "bogus", "target_path": "Z:/no/such/path/exists",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["warning"] and "not a directory" in body["warning"]


def test_folder_scan_real_dir(session_and_slug):
    """Scan the Forge platform dir itself — should find Python files."""
    import os
    s, slug = session_and_slug
    platform_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/kb/folder", json={
        "title": "platform source",
        "target_path": platform_dir,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["text_files"] >= 5, f"expected ≥5 text files, got {body}"


# -------------------- J6 replay harness --------------------

def test_replay_nonexistent_call_404(session_and_slug):
    s, _ = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/llm-calls/9999999/replay", json={})
    assert r.status_code == 404


def test_replay_call_without_prompt_422(session_and_slug):
    """NOT happy: some historical calls lack full_prompt (legacy). Replay must reject cleanly."""
    from app.database import SessionLocal
    from app.models import LLMCall, Project
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        call = LLMCall(
            project_id=proj.id, purpose="legacy", model="sonnet",
            prompt_hash="sha256:zero", prompt_preview="n/a",
            prompt_chars=0, response_chars=0, return_code=0,
            full_prompt=None,  # the trigger for 422
            response_text=None, cost_usd=0.0, model_used="sonnet", duration_ms=100,
        )
        db.add(call); db.commit(); cid = call.id
    finally:
        db.close()
    r = s.post(f"{BASE}/api/v1/tier1/llm-calls/{cid}/replay", json={})
    assert r.status_code == 422


# -------------------- F3 ROI + F4 marketplace --------------------

def test_roi_lookup_nonexistent_skill_404(session_and_slug):
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/skills/SK-nonexistent-xyz/roi")
    assert r.status_code == 404


def test_roi_builtin_skill_zero_invocations(session_and_slug):
    """Built-in skill that's not attached anywhere reports zero ROI."""
    s, _ = session_and_slug
    # Ensure seeded
    s.get(f"{BASE}/api/v1/skills")
    r = s.get(f"{BASE}/api/v1/skills/OP-best-dev-django/roi")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["eligible_for_marketplace"] is False


def test_promote_builtin_is_conflict(session_and_slug):
    s, _ = session_and_slug
    s.get(f"{BASE}/api/v1/skills")  # seed
    r = s.post(f"{BASE}/api/v1/skills/OP-best-dev-django/promote-to-org")
    assert r.status_code == 409


# -------------------- K1-K3 org views --------------------

def test_org_triage_shape(session_and_slug):
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/org/triage")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "open_items" in body
    for k in ("open_decisions", "failed_tasks", "findings_dismissed_no_reason"):
        assert k in body["open_items"]


def test_org_cross_project_patterns_shape(session_and_slug):
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/org/cross-project-patterns")
    assert r.status_code == 200
    assert "candidates" in r.json()


def test_org_budget_overview_last_30d(session_and_slug):
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/org/budget-overview")
    assert r.status_code == 200
    body = r.json()
    assert body["period"] == "last_30d"
    assert "total_usd" in body
    assert "per_project" in body
    assert "per_purpose" in body


def test_org_triage_requires_org_context():
    """Anon user without org must be blocked."""
    anon = requests.Session()
    r = anon.get(f"{BASE}/api/v1/tier1/org/triage")
    assert r.status_code in (401, 403)


# -------------------- L4 share-link business view --------------------

def test_share_link_business_view(session_and_slug):
    """NOT happy: business view must NOT leak internals like cost, llm_call_ids, prompts."""
    from app.database import SessionLocal
    from app.models import Project, Objective, ShareLink
    import secrets as sec
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        tok = sec.token_urlsafe(24)
        sl = ShareLink(project_id=proj.id, token=tok, scope="project",
                       created_by_user_id=None, revoked=False)
        db.add(sl); db.commit()
    finally:
        db.close()
    r = requests.get(f"{BASE}/share/{tok}")
    assert r.status_code == 200, r.text[:200]
    body = r.text
    # Must include objective business content
    assert "Shared project summary" in body
    assert "Objectives" in body
    # Must NOT leak sensitive terms
    for leak in ("prompt_text", "llm_call_id", "cost_usd", "forge_token"):
        assert leak not in body, f"share link leaks {leak}"
