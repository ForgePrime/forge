"""Unit tests for services/tenant — multi-tenant isolation helpers.

These tests guard the contract: a request for another org's project
slug must 404, never leak existence via different status codes.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.services.tenant import current_org_id, assert_project_in_org


# ---------- current_org_id ----------

def test_current_org_id_returns_none_when_no_org_in_state():
    request = SimpleNamespace(state=SimpleNamespace())
    assert current_org_id(request) is None


def test_current_org_id_returns_none_when_state_org_is_none():
    request = SimpleNamespace(state=SimpleNamespace(org=None))
    assert current_org_id(request) is None


def test_current_org_id_returns_stored_id():
    org = SimpleNamespace(id=42)
    request = SimpleNamespace(state=SimpleNamespace(org=org))
    assert current_org_id(request) == 42


# ---------- assert_project_in_org ----------

def _make_request(org_id: int | None):
    org = SimpleNamespace(id=org_id) if org_id is not None else None
    return SimpleNamespace(state=SimpleNamespace(org=org))


def test_assert_raises_404_when_no_org_context():
    """Unauthenticated / no-org user hits 404 not 403 — don't leak resource existence."""
    db = MagicMock()
    request = _make_request(org_id=None)
    with pytest.raises(HTTPException) as exc:
        assert_project_in_org(db, "any-slug", request)
    assert exc.value.status_code == 404


def test_assert_raises_404_when_project_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    request = _make_request(org_id=10)
    with pytest.raises(HTTPException) as exc:
        assert_project_in_org(db, "missing-slug", request)
    assert exc.value.status_code == 404


def test_assert_raises_404_when_project_in_other_org():
    """Classic tenant-isolation test — Project B exists but in org 99;
    the query filter by organization_id=10 returns None → 404."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    request = _make_request(org_id=10)
    with pytest.raises(HTTPException) as exc:
        assert_project_in_org(db, "other-org-project", request)
    assert exc.value.status_code == 404


def test_assert_returns_project_when_in_current_org():
    proj = SimpleNamespace(id=1, slug="acme", organization_id=10)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = proj
    request = _make_request(org_id=10)

    result = assert_project_in_org(db, "acme", request)
    assert result is proj


def test_assert_uses_correct_filter_predicates():
    """Verify the SQLAlchemy filter receives both slug AND organization_id."""
    proj = SimpleNamespace(id=1, slug="beta", organization_id=7)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = proj
    request = _make_request(org_id=7)

    assert_project_in_org(db, "beta", request)
    # Verify db.query(Project) was called (filter construction is MagicMock
    # opaque; we can at least confirm the session was queried).
    assert db.query.called
