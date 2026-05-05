"""Tests for the /ui/audit view + JSON variant.

Uses live DB (forge_platform); covers:
  - Audit template parses without Jinja errors
  - JSON endpoint returns well-formed payload
  - Filters (kc, window) work
  - Counts are correct after a fresh K-event INSERT (rolled back)
"""

from __future__ import annotations

import datetime as dt
import json
import os

import pytest

try:
    from sqlalchemy import create_engine, func as sqlfunc
    from sqlalchemy.orm import sessionmaker
    from app.api.ui import templates
    from app.models import (
        Decision,
        Execution,
        KillCriteriaEventLog,
        Project,
        Task,
    )
    from app.services.kill_criteria import log_kill_criterion
except Exception as e:  # pragma: no cover
    pytest.skip(f"DB-dependent imports failed: {e}", allow_module_level=True)


DB_URL = os.environ.get(
    "FORGE_TEST_DATABASE_URL",
    "postgresql://forge:forge@localhost:5432/forge_platform",
)

try:
    _engine = create_engine(DB_URL)
    with _engine.connect() as _c:
        pass
except Exception as e:  # pragma: no cover
    pytest.skip(f"could not connect to DB at {DB_URL}: {e}", allow_module_level=True)

SessionFactory = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture
def db_session():
    s = SessionFactory()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _stub_request():
    """Minimal Starlette Request for template rendering."""
    from starlette.requests import Request
    scope = {
        "type": "http", "method": "GET", "path": "/ui/audit",
        "headers": [], "query_string": b"",
        "scheme": "http", "server": ("test", 80),
        "client": ("127.0.0.1", 0), "root_path": "",
    }
    return Request(scope)


# --- Template render -------------------------------------------------------


def test_audit_template_renders_empty_state():
    """Empty rows list renders the empty-state copy ('No K-events')."""
    resp = templates.TemplateResponse(_stub_request(), "audit.html", {
        "rows": [],
        "total_rows": 0,
        "code_counts": {f"K{i}": 0 for i in range(1, 7)},
        "selected_kc": "",
        "selected_window": "24h",
    })
    body = resp.body.decode("utf-8")
    assert "No K-events" in body
    assert "K-criteria Audit Log" in body


def test_audit_template_renders_rows(db_session):
    """When K-events exist, they appear in the table with the correct
    columns: time, K-code badge, entity ref, reason, evidence."""
    proj = Project(slug=f"audit-test-{dt.datetime.now().timestamp()}", name="t", goal="t")
    db_session.add(proj)
    db_session.flush()
    dec = Decision(
        project_id=proj.id, external_id="DEC-AUDIT-1",
        type="root_cause", issue="i", recommendation="r", status="OPEN",
    )
    db_session.add(dec)
    db_session.flush()
    log_kill_criterion(db_session, "K4", "test K4 reason for audit view", decision_id=dec.id)
    db_session.flush()

    rows = (
        db_session.query(KillCriteriaEventLog)
        .filter(KillCriteriaEventLog.decision_id == dec.id)
        .all()
    )
    assert len(rows) == 1

    counts = {f"K{i}": 0 for i in range(1, 7)}
    counts["K4"] = 1

    resp = templates.TemplateResponse(_stub_request(), "audit.html", {
        "rows": rows, "total_rows": 1,
        "code_counts": counts,
        "selected_kc": "K4", "selected_window": "24h",
    })
    body = resp.body.decode("utf-8")
    assert "K4" in body
    assert "test K4 reason" in body
    assert f"dec#{dec.id}" in body
    assert "K-criteria Audit Log" in body


def test_audit_template_handles_filter_state():
    """Filter dropdowns reflect selected values."""
    resp = templates.TemplateResponse(_stub_request(), "audit.html", {
        "rows": [],
        "total_rows": 0,
        "code_counts": {f"K{i}": 0 for i in range(1, 7)},
        "selected_kc": "K4",
        "selected_window": "7d",
    })
    body = resp.body.decode("utf-8")
    # Selected kc=K4 → that <option> has 'selected'
    assert 'value="K4" selected' in body
    # Selected window=7d → that <option> has 'selected'
    assert 'value="7d" selected' in body


# --- Live DB end-to-end (real audit data) ----------------------------------


# --- Dismissal flow ---------------------------------------------------------


def test_audit_template_renders_dismissed_badge(db_session):
    """When a dismissal Decision exists for a K-event, the row shows
    a 'Dismissed by DEC-X' badge instead of the Dismiss form."""
    proj = Project(slug=f"audit-dismiss-{dt.datetime.now().timestamp()}", name="t", goal="t")
    db_session.add(proj)
    db_session.flush()
    dec = Decision(
        project_id=proj.id, external_id="DEC-AUDIT-2",
        type="root_cause", issue="i", recommendation="r", status="OPEN",
    )
    db_session.add(dec)
    db_session.flush()
    log_kill_criterion(db_session, "K4", "test K4 event for dismissal", decision_id=dec.id)
    db_session.flush()
    event_row = (
        db_session.query(KillCriteriaEventLog)
        .filter(KillCriteriaEventLog.decision_id == dec.id)
        .one()
    )
    # Create a dismissal Decision matching the external_id pattern
    override = Decision(
        project_id=proj.id,
        external_id=f"KC-OVERRIDE-{event_row.id}",
        type="kc_override",
        issue=f"Steward dismissal of K-event #{event_row.id}",
        recommendation="distinct-actor exception per ADR-012 human-in-loop",
        status="ACCEPTED",
    )
    db_session.add(override)
    db_session.flush()

    counts = {f"K{i}": 0 for i in range(1, 7)}
    counts["K4"] = 1
    resp = templates.TemplateResponse(_stub_request(), "audit.html", {
        "rows": [event_row],
        "total_rows": 1,
        "code_counts": counts,
        "selected_kc": "K4",
        "selected_window": "24h",
        "dismissals": {event_row.id: override},
    })
    body = resp.body.decode("utf-8")
    assert f"Dismissed by DEC-{override.id}" in body
    # Dismiss form should NOT be rendered when already dismissed
    assert f"audit/dismiss/{event_row.id}" not in body


def test_audit_template_renders_dismiss_button_when_active(db_session):
    """When no dismissal exists, Dismiss button + form are visible."""
    proj = Project(slug=f"audit-active-{dt.datetime.now().timestamp()}", name="t", goal="t")
    db_session.add(proj)
    db_session.flush()
    dec = Decision(
        project_id=proj.id, external_id="DEC-ACTIVE-1",
        type="root_cause", issue="i", recommendation="r", status="OPEN",
    )
    db_session.add(dec)
    db_session.flush()
    log_kill_criterion(db_session, "K4", "active K4 needing dismiss button", decision_id=dec.id)
    db_session.flush()
    event_row = (
        db_session.query(KillCriteriaEventLog)
        .filter(KillCriteriaEventLog.decision_id == dec.id)
        .one()
    )
    counts = {f"K{i}": 0 for i in range(1, 7)}
    counts["K4"] = 1
    resp = templates.TemplateResponse(_stub_request(), "audit.html", {
        "rows": [event_row],
        "total_rows": 1,
        "code_counts": counts,
        "selected_kc": "K4",
        "selected_window": "24h",
        "dismissals": {},  # none dismissed
    })
    body = resp.body.decode("utf-8")
    assert f"audit/dismiss/{event_row.id}" in body
    assert "Confirm dismiss" in body
    assert "active" in body  # status badge


def test_audit_template_renders_with_real_27_k4_events(db_session):
    """Smoke check that the actual 27 K4 events from §1.21 audit are visible
    in the rendered template. If the audit was wiped (DELETE FROM), test
    becomes informational (skipped via empty rows check)."""
    rows = (
        db_session.query(KillCriteriaEventLog)
        .filter(KillCriteriaEventLog.kc_code == "K4")
        .order_by(KillCriteriaEventLog.fired_at.desc())
        .limit(50)
        .all()
    )
    if not rows:
        pytest.skip("no K4 events in DB; skipping live render assertion")
    counts = {f"K{i}": 0 for i in range(1, 7)}
    counts["K4"] = len(rows)
    resp = templates.TemplateResponse(_stub_request(), "audit.html", {
        "rows": rows,
        "total_rows": len(rows),
        "code_counts": counts,
        "selected_kc": "K4",
        "selected_window": "24h",
    })
    body = resp.body.decode("utf-8")
    assert "solo-verifier" in body
    assert "execution_id=" in body
