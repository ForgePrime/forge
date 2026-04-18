"""Tier-1 UI catch-up — non-happy-path smoke that verifies the templates render
the new panels/tabs/badges introduced for B1, G1, D2, B2, D1, L1.

Why non-happy:
- Empty-project case (no tasks/objectives/findings) is the FIRST thing a user sees.
  If the UI assumes data exists, it crashes here. Verifying empty path protects all paths.
- Templates that conditionally render (jinja {% if %}) are the silent fail mode —
  a missing context key shows blank, no error. We assert markers explicitly.

Coverage map:
- B1 trust-debt panel: t1, t2  (rendered with all-zero, anchor links present)
- G1 contract tab:    t3, t4  (tab visible; editor renders existing content)
- L1 docs tab:         t5     (heading present; auto-generated structure markers)
- D2 reopen modal:     t6     (button absent on ACTIVE objective; present on ACHIEVED)
- B2 AC source badge:  t7     (UNSOURCED badge rendered when source_ref NULL)
- D1 task type:        t8     (4 new types in <select>; legacy 4 still present)
"""
import os
import re
import time
import pytest
import requests
from sqlalchemy import text

BASE = os.environ.get("FORGE_TEST_BASE", "http://127.0.0.1:8063")
TS = int(time.time())


@pytest.fixture(scope="module")
def session_and_slug():
    s = requests.Session()
    r = s.post(f"{BASE}/ui/signup", data={
        "email": f"t1ui-{TS}@t.com", "password": "pw-test-12345", "full_name": "T1 UI",
        "org_slug": f"t1ui-{TS}", "org_name": "T1 UI Org",
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"t1ui-{TS}"
    r = s.post(f"{BASE}/ui/projects",
               data={"slug": slug, "name": "T1 UI", "goal": "ui smoke"},
               allow_redirects=False)
    assert r.status_code == 303
    return s, slug


def test_t1_dashboard_trust_debt_panel_renders_with_zeros(session_and_slug):
    """NOT happy: brand-new org has zero debt — panel must still render with friendly state."""
    s, _ = session_and_slug
    r = s.get(f"{BASE}/ui/")
    assert r.status_code == 200
    html = r.text
    assert "Your audit queue" in html, "trust-debt panel header missing"
    for label in ("Unaudited approvals", "Manual scenarios unrun",
                  "Dismissed without reason", "Stale analyses"):
        assert label in html, f"counter '{label}' missing"
    assert "No outstanding scrutiny debt" in html, "all-zero friendly state missing"


def test_t2_dashboard_panel_links_to_filter_views(session_and_slug):
    """NOT happy: counters must be navigable. Even if filter URLs aren't implemented yet,
    the anchors must exist so we don't ship dead UI."""
    s, _ = session_and_slug
    r = s.get(f"{BASE}/ui/")
    for q in ("?filter=unaudited", "?filter=manual_unrun",
              "?filter=dismissed_no_reason", "?filter=stale"):
        assert q in r.text, f"anchor for {q} missing"


def test_t3_contract_tab_visible_in_project(session_and_slug):
    """NOT happy: tab must show in nav. Empty contract — editor still renders."""
    s, slug = session_and_slug
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=contract")
    assert r.status_code == 200
    html = r.text
    assert "?tab=contract" in html, "contract tab link missing"
    assert "Operational contract" in html, "contract tab heading missing"
    assert 'name="contract_md"' in html, "textarea missing"


def test_t4_contract_tab_round_trip_via_endpoint(session_and_slug):
    """NOT happy: save then reload — content must persist + render in textarea."""
    s, slug = session_and_slug
    needle = f"## CONTRACT-NEEDLE-{TS}\n- on-prem only"
    r = s.put(f"{BASE}/api/v1/tier1/projects/{slug}/contract",
              json={"contract_md": needle})
    assert r.status_code == 200
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=contract")
    assert needle in r.text, "saved contract did not render in textarea"


def test_t5_docs_tab_renders_auto_markdown(session_and_slug):
    """NOT happy: empty project — docs must still produce structure markers (no LLM)."""
    s, slug = session_and_slug
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=docs")
    assert r.status_code == 200, r.text[:200]
    for needle in ("Documentation (auto-generated)",
                   "## Pipeline status",
                   "## Changelog",
                   "## Findings audit",
                   "## Cost ledger"):
        assert needle in r.text, f"docs missing '{needle}'"


def test_t6_reopen_button_only_on_achieved_objective(session_and_slug):
    """NOT happy: ACTIVE objective should NOT show re-open button (would let user push
    backwards into nothing). ACHIEVED objective MUST show it."""
    from app.database import SessionLocal
    from app.models import Project, Objective
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        # Only one objective allowed per external_id, so create per-test variants
        for ext, status in [("O-T6A", "ACTIVE"), ("O-T6B", "ACHIEVED")]:
            obj = Objective(project_id=proj.id, external_id=ext,
                            title=f"obj {ext}", business_context="ctx" * 10,
                            status=status, priority=3)
            db.add(obj)
        db.commit()
    finally:
        db.close()

    r = s.get(f"{BASE}/ui/projects/{slug}?tab=objectives")
    html = r.text
    # ACTIVE: re-open button absent
    active_block = html.split('id="obj-O-T6A"')[1].split('id="obj-O-T6B"')[0]
    assert "↶ Re-open" not in active_block, "ACTIVE objective should not show re-open button"
    assert "Plan →" in active_block, "ACTIVE objective should show Plan button"
    # ACHIEVED: re-open button present + modal exists
    achieved_block = html.split('id="obj-O-T6B"')[1]
    assert "↶ Re-open" in achieved_block, "ACHIEVED objective must show re-open button"
    assert 'id="reopen-modal-O-T6B"' in achieved_block, "modal markup missing"
    assert 'name="gap_notes"' in achieved_block


def test_t7_unsourced_ac_badge_renders(session_and_slug):
    """NOT happy: AC with NULL source_ref must show "INVENTED BY LLM" warning."""
    from app.database import SessionLocal
    from app.models import Project, Task, AcceptanceCriterion
    s, slug = session_and_slug
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        t = Task(project_id=proj.id, external_id="T-T7", name="badge-test",
                 instruction="instruction long enough", type="develop", status="DONE")
        db.add(t); db.flush()
        db.add(AcceptanceCriterion(task_id=t.id, position=0,
                                   text="Endpoint must return 200 on valid input.",
                                   scenario_type="positive", verification="manual",
                                   source_ref=None))
        db.add(AcceptanceCriterion(task_id=t.id, position=1,
                                   text="Endpoint rejects invalid input with 422.",
                                   scenario_type="negative", verification="test",
                                   source_ref="SRC-001 §4.2"))
        db.commit()
    finally:
        db.close()

    r = s.get(f"{BASE}/ui/projects/{slug}/tasks/T-T7")
    assert r.status_code == 200, r.text[:300]
    html = r.text
    assert "INVENTED BY LLM" in html, "unsourced AC must show warning badge"
    assert "SRC-001 §4.2" in html, "sourced AC must show source attribution badge"


def test_t8_task_form_lists_all_8_types(session_and_slug):
    """NOT happy: form must accept new + legacy types so both flows work."""
    s, slug = session_and_slug
    r = s.get(f"{BASE}/ui/projects/{slug}?tab=tasks")
    html = r.text
    for new in ("analysis", "planning", "develop", "documentation"):
        assert f'value="{new}"' in html, f"new type '{new}' missing from form"
    for legacy in ("feature", "bug", "chore", "investigation"):
        assert f'value="{legacy}"' in html, f"legacy type '{legacy}' missing"
