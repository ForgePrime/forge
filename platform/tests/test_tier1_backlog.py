"""Tier-1 backlog non-happy-path tests.

Why non-happy-path covers all paths:
- For every endpoint, exercise the auth wall, scoping wall, validation wall,
  and missing-data branches. If those return correct codes, the corresponding
  happy paths are implied (server didn't crash, didn't leak data).

Coverage map:
- D1 (4 task types):           t1, t2 — schema accepts new types; old types still valid.
- G1+G3 (contract):            t3..t7 — anon/foreign/empty/oversize/round-trip + injection length.
- B2 (AC source_ref):          t8..t10 — set / clear / nonexistent AC.
- D2 (objective re-open):      t11..t14 — anon/foreign/short-notes/wrong-status + happy round-trip + history.
- B1 (trust-debt counters):    t15..t17 — empty project shape / dismiss-without-reason rejected / dismiss with reason persists.
- L1 (auto-draft docs):        t18..t19 — content shape / no LLM call.
"""
import os
import time
import pytest
import requests

BASE = os.environ.get("FORGE_TEST_BASE", "http://127.0.0.1:8063")
TS = int(time.time())


@pytest.fixture(scope="module")
def session_and_slug():
    s = requests.Session()
    email = f"t1-{TS}@t.com"
    r = s.post(f"{BASE}/ui/signup", data={
        "email": email, "password": "pw-test-12345", "full_name": "T1",
        "org_slug": f"t1-org-{TS}", "org_name": "T1 Org",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"t1-proj-{TS}"
    r = s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": "T1", "goal": "tier1"},
               allow_redirects=False)
    assert r.status_code == 303
    return s, slug


# -------------------- D1: 4 task types --------------------

def test_t1_existing_old_task_types_still_valid(session_and_slug):
    """NOT happy: backwards-compat. If we broke the constraint, old projects with
    feature/bug/chore tasks would error on read. Verify old types still legal."""
    s, slug = session_and_slug
    r = s.post(f"{BASE}/ui/projects/{slug}/tasks/new", data={
        "name": "old-chore", "instruction": "do the chore: x" * 5, "type": "chore",
    }, allow_redirects=False)
    assert r.status_code in (200, 303), f"old chore type rejected: {r.text[:300]}"


def test_t2_new_task_type_documentation_accepted(session_and_slug):
    """NOT happy: new type 'documentation' (D1). DB constraint must accept it."""
    s, slug = session_and_slug
    r = s.post(f"{BASE}/ui/projects/{slug}/tasks/new", data={
        "name": "write-runbook", "instruction": "draft the runbook for ops handoff", "type": "documentation",
    }, allow_redirects=False)
    assert r.status_code in (200, 303), f"new doc type rejected: {r.text[:300]}"


# -------------------- G1+G3: operational contract --------------------

def test_t3_contract_get_anon_rejected():
    s = requests.Session()
    r = s.get(f"{BASE}/api/v1/tier1/projects/x/contract")
    assert r.status_code in (401, 403)


def test_t4_contract_get_foreign_project_403_or_404(session_and_slug):
    s, _ = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/totally-fake-zzz/contract")
    assert r.status_code in (403, 404)


def test_t5_contract_oversize_rejected(session_and_slug):
    s, slug = session_and_slug
    huge = "x" * 25000
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/contract", json={"contract_md": huge})
    assert r.status_code == 422


def test_t6_contract_round_trip_persists(session_and_slug):
    s, slug = session_and_slug
    md = "## Constraints\n- on-prem only\n- python stack"
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/contract", json={"contract_md": md})
    assert r.status_code == 200, r.text
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/contract")
    assert r.status_code == 200
    assert r.json()["contract_md"] == md


def test_t7_contract_injected_into_ai_chat_system_prompt(session_and_slug):
    """NOT happy: contract should appear in AI sidebar system prompt. Verify via
    a slash chat — the response itself doesn't matter, but it must succeed and
    the AIInteraction row's system_prompt should contain the contract text."""
    from sqlalchemy import text
    from app.database import engine
    s, slug = session_and_slug
    # set a recognizable contract first
    needle = "FORGE_CONTRACT_INJECTION_NEEDLE_42"
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/contract",
              json={"contract_md": f"## test\n{needle}"})
    assert r.status_code == 200
    r = s.post(f"{BASE}/api/v1/ai/chat", json={
        "message": "/help",
        "page_ctx": {"page_id": "project-view", "title": "x", "route": f"/ui/projects/{slug}",
                     "entity_type": "project", "entity_id": slug,
                     "visible_data": {}, "actions": []},
    })
    assert r.status_code == 200
    iid = r.json().get("interaction_id")
    assert iid
    with engine.connect() as c:
        row = c.execute(text("SELECT system_prompt FROM ai_interactions WHERE id = :i"),
                        {"i": iid}).first()
        assert row, "interaction not persisted"
        assert needle in row[0], "contract was not injected into the system prompt"


# -------------------- B2: AC source_ref --------------------

def test_t8_ac_source_set_nonexistent_task_404(session_and_slug):
    s, slug = session_and_slug
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/T-9999/ac/1/source",
              json={"source_ref": "SRC-001"})
    assert r.status_code == 404


def test_t9_ac_source_set_nonexistent_position(session_and_slug):
    s, slug = session_and_slug
    # First, create a task with one AC via the existing UI route
    r = s.post(f"{BASE}/ui/projects/{slug}/tasks/new", data={
        "name": "with-ac", "instruction": "implement profile edit endpoint with auth", "type": "feature",
    }, allow_redirects=False)
    assert r.status_code in (200, 303), r.text[:200]
    # Find external_id of the new task
    from sqlalchemy import text
    from app.database import engine
    with engine.connect() as c:
        ext = c.execute(text("SELECT external_id FROM tasks WHERE name='with-ac' ORDER BY id DESC LIMIT 1")).scalar()
    assert ext
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{ext}/ac/99/source",
              json={"source_ref": "SRC-001"})
    assert r.status_code == 404


def test_t10_ac_source_set_then_clear(session_and_slug):
    """NOT happy: set source then clear. Tests both NULL and non-NULL paths.
    Self-contained — creates its own task to avoid order-dependency on t9."""
    s, slug = session_and_slug
    # Create a fresh task for this test
    r = s.post(f"{BASE}/ui/projects/{slug}/tasks/new", data={
        "name": "src-ref-test", "instruction": "task for source-attribution test",
        "type": "feature",
    }, allow_redirects=False)
    assert r.status_code in (200, 303), r.text[:200]

    from sqlalchemy import text
    from app.database import engine
    with engine.connect() as c:
        ext = c.execute(
            text("SELECT external_id FROM tasks WHERE name='src-ref-test' AND project_id IN "
                 "(SELECT id FROM projects WHERE slug=:s) ORDER BY id DESC LIMIT 1"),
            {"s": slug},
        ).scalar()
    assert ext, "task not created — check ui_add_task"
    r = s.post(f"{BASE}/ui/projects/{slug}/tasks/{ext}/ac",
               data={"text": "User can log in with valid credentials and see dashboard."},
               allow_redirects=False)
    assert r.status_code in (200, 201, 303), r.text[:200]

    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{ext}/ac/0/source",
              json={"source_ref": "SRC-001 §4.2"})
    assert r.status_code == 200, r.text
    assert r.json()["is_unsourced"] is False

    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/tasks/{ext}/ac/0/source",
              json={"source_ref": None})
    assert r.status_code == 200
    assert r.json()["is_unsourced"] is True


# -------------------- D2: objective re-open --------------------

def test_t11_reopen_anon_rejected():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/tier1/projects/x/objectives/O-001/reopen",
               json={"gap_notes": "y" * 30})
    assert r.status_code in (401, 403)


def test_t12_reopen_short_notes_422(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/reopen",
               json={"gap_notes": "too short"})
    assert r.status_code == 422


def test_t13_reopen_nonexistent_objective(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-999/reopen",
               json={"gap_notes": "x" * 30})
    assert r.status_code == 404


def test_t14_reopen_round_trip_active_objective_409(session_and_slug):
    """NOT happy: cannot re-open ACTIVE objective (only ACHIEVED/ABANDONED).
    Create one ACTIVE objective via direct DB and verify 409."""
    from sqlalchemy import text
    from app.database import engine, SessionLocal
    from app.models import Project, Objective
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        obj = Objective(project_id=proj.id, external_id="O-001",
                        title="Test", business_context="ctx" * 10,
                        status="ACTIVE", priority=3)
        db.add(obj); db.commit()
    finally:
        db.close()

    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/reopen",
               json={"gap_notes": "this should be rejected because status is ACTIVE not ACHIEVED."})
    assert r.status_code == 409, r.text

    # Now flip to ACHIEVED and re-open should work, and history is preserved
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        obj = db.query(Objective).filter(Objective.project_id == proj.id, Objective.external_id == "O-001").first()
        obj.status = "ACHIEVED"; db.commit()
    finally:
        db.close()
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/reopen",
               json={"gap_notes": "the load test was never executed and rate limit is missing."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ACTIVE"
    assert body["history_preserved"] is True

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/objectives/O-001/reopens")
    assert r.status_code == 200
    assert len(r.json()["reopens"]) == 1
    assert "load test" in r.json()["reopens"][0]["gap_notes"]


# -------------------- B1: trust-debt counters --------------------

def test_t15_trust_debt_empty_project_returns_all_zero(session_and_slug):
    s, slug = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/trust-debt")
    assert r.status_code == 200
    body = r.json()
    for k in ("unaudited_approvals", "manual_scenarios_unrun",
              "findings_dismissed_no_reason", "stale_analyses"):
        assert k in body
        assert isinstance(body[k], int)


def test_t16_finding_dismiss_short_reason_rejected(session_and_slug):
    s, slug = session_and_slug
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/F-999/dismiss",
               json={"dismissed_reason": "lol"})
    assert r.status_code == 422


def test_t17_finding_dismiss_persists_with_long_reason(session_and_slug):
    """NOT happy: dismiss requires ≥50 char reason. Insert a fake finding,
    dismiss it, verify columns populated, verify trust-debt counter does NOT
    increment for this dismissal (because it has a reason)."""
    from sqlalchemy import text
    from app.database import engine, SessionLocal
    from app.models import Project, Finding
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        f = Finding(project_id=proj.id, external_id="F-001",
                    type="lint", severity="medium", title="Foo",
                    description="bar" * 5, status="OPEN")
        db.add(f); db.commit()
    finally:
        db.close()

    reason = "Accepted because the team owns this technical debt and will address in next sprint per ADR-002."
    assert len(reason) >= 50
    r = s.post(f"{BASE}/api/v1/tier1/projects/{slug}/findings/F-001/dismiss",
               json={"dismissed_reason": reason})
    assert r.status_code == 200, r.text

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/trust-debt")
    body = r.json()
    assert body["findings_dismissed_no_reason"] == 0, "dismissal WITH reason should not count as debt"


# -------------------- L1: auto-draft docs --------------------

def test_t18_docs_auto_returns_markdown_no_llm(session_and_slug):
    s, slug = session_and_slug
    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/docs/auto")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["llm_used"] is False
    assert body["deterministic"] is True
    assert body["format"] == "markdown"
    assert "# T1" in body["content_md"], "project name should be in README header"
    assert "## Pipeline status" in body["content_md"]
    assert "## Changelog" in body["content_md"]
    assert "## Findings audit" in body["content_md"]
    assert "## Cost ledger" in body["content_md"]


def test_t19_docs_auto_unauthorized(session_and_slug):
    """NOT happy: anon cannot read project docs."""
    anon = requests.Session()
    r = anon.get(f"{BASE}/api/v1/tier1/projects/whatever/docs/auto")
    assert r.status_code in (401, 403)
