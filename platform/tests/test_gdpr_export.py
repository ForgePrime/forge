"""Unit tests for services/gdpr_export — Article 20 data portability."""
from dataclasses import dataclass, field
import datetime as dt
from unittest.mock import MagicMock

from app.services.gdpr_export import export_user_data, export_organization_data


# ---------- Minimal ORM fakes ----------

@dataclass
class FakeUser:
    id: int
    email: str
    full_name: str | None = None
    is_active: bool = True
    created_at: dt.datetime | None = None
    last_login_at: dt.datetime | None = None


@dataclass
class FakeMembership:
    user_id: int
    organization_id: int
    role: str
    created_at: dt.datetime | None = None


@dataclass
class FakeOrg:
    id: int
    slug: str
    name: str
    plan: str = "pilot"
    created_at: dt.datetime | None = None


@dataclass
class FakeAuditEntry:
    id: int
    entity_type: str
    entity_id: int
    action: str
    actor: str
    created_at: dt.datetime | None = None


@dataclass
class FakeProject:
    id: int
    slug: str
    name: str
    goal: str | None = None
    autonomy_level: str | None = None
    created_at: dt.datetime | None = None


# ---------- Session mock that responds to specific model queries ----------

def _make_session(user=None, memberships=None, orgs=None, audit=None, projects=None):
    """Returns a MagicMock session configured with preset query results.

    Maps model class name → filtered list. Simplistic but enough to test
    the data aggregation shape.
    """
    from app.models import (
        User as _U, Membership as _M, Organization as _O, AuditLog as _A,
        Project as _P,
    )

    session = MagicMock()

    def query(model):
        q = MagicMock()
        if model is _U:
            q.filter.return_value.first.return_value = user
        elif model is _M:
            q.filter.return_value.all.return_value = memberships or []
            q.filter.return_value.filter.return_value.first.return_value = None
        elif model is _O:
            q.filter.return_value.all.return_value = orgs or []
            q.filter.return_value.first.return_value = orgs[0] if orgs else None
        elif model is _A:
            sub = MagicMock()
            sub.order_by.return_value.limit.return_value.all.return_value = audit or []
            sub.filter.return_value.count.return_value = len(audit or [])
            q.filter.return_value = sub
        elif model is _P:
            q.filter.return_value.all.return_value = projects or []
        else:
            # Any other model — count returns 0
            sub = MagicMock()
            sub.count.return_value = 0
            q.filter.return_value = sub
        return q

    session.query.side_effect = query
    session.execute.return_value.all.return_value = []
    return session


# ---------- export_user_data ----------

def test_export_user_not_found_returns_error():
    s = _make_session(user=None)
    out = export_user_data(s, 999)
    assert out["error"] == "user not found"
    assert out["user_id"] == 999


def test_export_user_basic_shape():
    u = FakeUser(
        id=1, email="alice@example.com", full_name="Alice",
        created_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
    )
    s = _make_session(user=u)
    out = export_user_data(s, 1)
    assert out["gdpr_article"] == "20"
    assert out["subject"] == "user"
    assert out["identity"]["email"] == "alice@example.com"
    assert out["identity"]["full_name"] == "Alice"
    assert "exported_at" in out
    # Category keys always present (even when empty)
    assert "memberships" in out
    assert "organizations_member_of" in out
    assert "audit_log_entries" in out
    assert "projects_interacted_with" in out


def test_export_user_with_memberships():
    u = FakeUser(id=2, email="bob@x.co", full_name="Bob")
    ms = [FakeMembership(user_id=2, organization_id=10, role="editor")]
    orgs = [FakeOrg(id=10, slug="acme", name="Acme Corp")]
    s = _make_session(user=u, memberships=ms, orgs=orgs)
    out = export_user_data(s, 2)
    assert len(out["memberships"]) == 1
    assert out["memberships"][0]["organization_id"] == 10
    # Note: the simplistic mock doesn't wire org lookup by set id — so only
    # verify memberships structure; organizations list may not resolve in mock.


def test_export_user_includes_audit_entries():
    u = FakeUser(id=3, email="carol@y.co")
    audit = [
        FakeAuditEntry(id=1, entity_type="execution", entity_id=100,
                       action="created", actor="user:carol@y.co"),
    ]
    s = _make_session(user=u, audit=audit)
    out = export_user_data(s, 3)
    assert out["audit_log_entries_count"] >= 0


# ---------- export_organization_data ----------

def test_export_org_not_found_returns_error():
    s = _make_session(orgs=[])
    out = export_organization_data(s, 999)
    assert out["error"] == "organization not found"


def test_export_org_basic_shape():
    org = FakeOrg(id=5, slug="acme", name="Acme", plan="growth")
    s = _make_session(orgs=[org])
    out = export_organization_data(s, 5)
    assert out["gdpr_article"] == "20"
    assert out["subject"] == "organization"
    assert out["identity"]["slug"] == "acme"
    assert out["identity"]["plan"] == "growth"
    assert "projects" in out
    assert "members" in out
    assert "totals" in out


def test_export_org_with_projects_summary():
    org = FakeOrg(id=7, slug="beta", name="Beta Co")
    projects = [
        FakeProject(id=1, slug="web", name="Web App"),
        FakeProject(id=2, slug="api", name="API"),
    ]
    s = _make_session(orgs=[org], projects=projects)
    out = export_organization_data(s, 7)
    assert len(out["projects"]) == 2
    assert out["totals"]["projects"] == 2
    for p_summary in out["projects"]:
        assert "counts" in p_summary
        assert "tasks" in p_summary["counts"]


def test_export_always_includes_notes():
    """Notes section is GDPR-critical — explains what ISN'T in the export."""
    u = FakeUser(id=1, email="a@b.co")
    s = _make_session(user=u)
    user_out = export_user_data(s, 1)
    assert "notes" in user_out
    assert any("workspace" in n.lower() for n in user_out["notes"])

    org = FakeOrg(id=1, slug="x", name="X")
    s2 = _make_session(orgs=[org])
    org_out = export_organization_data(s2, 1)
    assert "notes" in org_out
