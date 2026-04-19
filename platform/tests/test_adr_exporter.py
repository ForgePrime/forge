"""Unit tests for services/adr_exporter — CGAID artifact #5 in-repo ADR export."""
import pathlib
import datetime as dt
from dataclasses import dataclass

from app.services.adr_exporter import _render_adr, _slug_title, export_decision


@dataclass
class FakeDecision:
    external_id: str
    issue: str
    recommendation: str
    reasoning: str | None = None
    status: str = "CLOSED"
    severity: str | None = None
    type: str | None = None
    confidence: str | None = None
    task_id: int | None = None
    created_at: dt.datetime | None = None


@dataclass
class FakeProject:
    slug: str


# ---------- _slug_title ----------

def test_slug_title_alphanumeric_only():
    assert _slug_title("Use PostgreSQL for audit log") == "use-postgresql-for-audit-log"


def test_slug_title_punctuation_and_diacritics():
    r = _slug_title("Kwestia: rezerwacje/blokady stanu — PostgreSQL?")
    assert all(c.isalnum() or c == "-" for c in r)
    assert "postgresql" in r


def test_slug_title_truncates():
    assert len(_slug_title("x" * 200, max_len=30)) <= 30


# ---------- _render_adr structure ----------

def test_render_adr_contains_nygard_sections():
    d = FakeDecision(
        external_id="D-001",
        issue="Which DB for audit log?",
        recommendation="Use PostgreSQL JSONB column with GIN index.",
        reasoning="Considered MongoDB, Elasticsearch, and PG. PG chosen for transactional consistency.",
        status="CLOSED", severity="medium",
    )
    md = _render_adr(d)
    assert "# D-001" in md
    assert "Which DB for audit log?" in md
    assert "## Status" in md
    assert "## Context" in md
    assert "## Decision" in md
    assert "## Alternatives considered" in md
    assert "## Consequences" in md
    assert "CLOSED" in md
    assert "PostgreSQL" in md


def test_render_adr_missing_fields_handled():
    """Decision with minimal data still produces valid markdown."""
    d = FakeDecision(
        external_id="D-007",
        issue="",
        recommendation="",
        status="CLOSED",
    )
    md = _render_adr(d)
    assert "D-007" in md
    assert "## Status" in md
    assert "no context captured" in md
    assert "no decision captured" in md


def test_render_adr_linked_task_in_consequences():
    d = FakeDecision(
        external_id="D-042",
        issue="Rate limit shape",
        recommendation="Token bucket per-user, 60 req/min burst 10",
        status="CLOSED",
    )
    md = _render_adr(d, task_ext_id="T-123")
    assert "T-123" in md
    assert "Linked task" in md


def test_render_adr_metadata_trailer():
    d = FakeDecision(
        external_id="D-099",
        issue="test",
        recommendation="test",
        status="CLOSED",
        created_at=dt.datetime(2026, 4, 19, 10, 0, tzinfo=dt.timezone.utc),
    )
    md = _render_adr(d)
    assert "D-099" in md.split("---")[-1]
    assert "2026-04-19" in md


# ---------- export_decision (filesystem) ----------

def test_export_decision_writes_file(tmp_path):
    proj = FakeProject(slug="test-proj")
    d = FakeDecision(
        external_id="D-001", issue="Use PostgreSQL", recommendation="Yes", status="CLOSED",
    )
    path = export_decision(d, proj, str(tmp_path))
    assert path is not None
    assert path.exists()
    # Path structure: {root}/{slug}/workspace/.ai/decisions/D-001-use-postgresql.md
    assert path.parent.name == "decisions"
    assert path.parent.parent.name == ".ai"
    assert "D-001" in path.name
    content = path.read_text(encoding="utf-8")
    assert "Use PostgreSQL" in content


def test_export_decision_skips_open(tmp_path):
    proj = FakeProject(slug="test-proj")
    d = FakeDecision(
        external_id="D-002", issue="?", recommendation="?", status="OPEN",
    )
    path = export_decision(d, proj, str(tmp_path))
    assert path is None


def test_export_decision_creates_dir_tree(tmp_path):
    """Workspace dir doesn't exist yet — exporter creates full tree."""
    proj = FakeProject(slug="new-proj")
    d = FakeDecision(external_id="D-003", issue="x", recommendation="y", status="CLOSED")
    path = export_decision(d, proj, str(tmp_path))
    assert path is not None
    assert (tmp_path / "new-proj" / "workspace" / ".ai" / "decisions").exists()


def test_export_decision_filename_deterministic(tmp_path):
    """Same decision written twice → same filename (idempotent overwrite)."""
    proj = FakeProject(slug="x")
    d = FakeDecision(
        external_id="D-100", issue="Same title", recommendation="same", status="CLOSED",
    )
    p1 = export_decision(d, proj, str(tmp_path))
    p2 = export_decision(d, proj, str(tmp_path))
    assert p1 == p2
    assert p1.exists()
