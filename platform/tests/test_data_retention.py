"""Unit tests for services/data_retention — GDPR storage-limitation sweep."""
import datetime as dt
from unittest.mock import MagicMock

from app.services.data_retention import (
    sweep, RetentionPolicy, RETENTION_POLICIES,
    _resolve_model,
)


# ---------- Default policy shape ----------

def test_default_policies_present():
    """3 default policies: LLMCall, AuditLog, OrchestrateRun.

    (PromptElement needs TimestampMixin schema migration before it can
    join defaults — documented in RETENTION_POLICIES module header.)
    """
    names = {p.entity for p in RETENTION_POLICIES}
    assert names == {"LLMCall", "AuditLog", "OrchestrateRun"}


def test_default_policies_have_rationale():
    """Every TTL has a stated rationale — prevents drift to magic numbers."""
    for p in RETENTION_POLICIES:
        assert p.rationale
        assert len(p.rationale) > 20
        assert p.ttl_days > 0


def test_ttl_days_are_pii_conservative():
    """Prompt-body entities must not retain > 1 year (PII minimization)."""
    for p in RETENTION_POLICIES:
        if p.entity in ("LLMCall", "PromptElement"):
            assert p.ttl_days <= 365, (
                f"{p.entity} TTL ({p.ttl_days}d) exceeds 1y — "
                "tighten for PII minimization"
            )


def test_resolve_model_returns_none_for_unknown():
    assert _resolve_model("NonExistentModel") is None


# ---------- sweep() structured output ----------

def _mock_db(counts_by_model: dict[str, int]):
    """Build a MagicMock session that returns a preset count per model name."""
    from app import models

    session = MagicMock()

    def query(model):
        q = MagicMock()
        name = model.__name__
        count = counts_by_model.get(name, 0)
        q.filter.return_value.count.return_value = count
        q.filter.return_value.delete.return_value = count
        return q

    session.query.side_effect = query
    return session


def test_sweep_dry_run_reports_counts_no_delete():
    db = _mock_db({"LLMCall": 42, "AuditLog": 0, "OrchestrateRun": 3})
    result = sweep(db, dry_run=True)
    assert result["dry_run"] is True
    # Totals reflect "would delete" in dry-run (42 + 0 + 3)
    assert result["totals"]["would_delete"] == 45
    assert result["totals"]["deleted"] == 0
    # Every policy appears in the report
    entity_names = {p["entity"] for p in result["policies"]}
    assert entity_names >= {"LLMCall", "AuditLog", "OrchestrateRun"}


def test_sweep_reports_cutoff_per_entity():
    """Each policy result includes the ISO-formatted cutoff timestamp."""
    db = _mock_db({})
    result = sweep(db, dry_run=True)
    for p in result["policies"]:
        assert "cutoff" in p
        # ISO format check: starts with YYYY-MM-DD
        assert p["cutoff"][:4].isdigit()


def test_sweep_restricts_to_entities_subset():
    db = _mock_db({"LLMCall": 5, "AuditLog": 9})
    result = sweep(db, dry_run=True, entities=["LLMCall"])
    entities = {p["entity"] for p in result["policies"]}
    assert entities == {"LLMCall"}


def test_sweep_override_ttl_for_single_entity():
    """Overrides map tightens the TTL for one entity without affecting others."""
    db = _mock_db({})
    # Override LLMCall to 30 days (tight)
    result = sweep(db, dry_run=True, overrides={"LLMCall": 30})
    llm_entry = next(p for p in result["policies"] if p["entity"] == "LLMCall")
    other = next(p for p in result["policies"] if p["entity"] == "AuditLog")
    assert llm_entry["ttl_days"] == 30
    assert other["ttl_days"] == 365  # default unchanged


def test_sweep_deterministic_executed_at():
    """Injected clock → reproducible executed_at (for tests + audit)."""
    clock = dt.datetime(2026, 4, 19, 12, 0, tzinfo=dt.timezone.utc)
    db = _mock_db({})
    r = sweep(db, dry_run=True, now=clock)
    assert r["executed_at"] == clock.isoformat()


def test_sweep_real_delete_path_updates_totals():
    db = _mock_db({"LLMCall": 10, "AuditLog": 5, "OrchestrateRun": 0})
    result = sweep(db, dry_run=False)
    assert result["dry_run"] is False
    # deleted sums across all policies (10 + 5 + 0)
    assert result["totals"]["deleted"] == 15


def test_sweep_captures_per_entity_errors():
    """A single entity's failure doesn't abort the sweep — error is reported."""
    from app import models

    session = MagicMock()
    call_count = {"n": 0}

    def query(model):
        q = MagicMock()
        # Raise on LLMCall, succeed on others
        if model.__name__ == "LLMCall":
            q.filter.return_value.count.side_effect = RuntimeError("db transient")
        else:
            q.filter.return_value.count.return_value = 0
            q.filter.return_value.delete.return_value = 0
        return q

    session.query.side_effect = query
    result = sweep(session, dry_run=False)
    llm_row = next(p for p in result["policies"] if p["entity"] == "LLMCall")
    assert llm_row["error"] is not None
    assert "db transient" in llm_row["error"]
    # Other entities still ran
    other_entities = [p for p in result["policies"] if p["entity"] != "LLMCall"]
    assert all(p["error"] is None for p in other_entities)


def test_sweep_custom_policy_via_override_does_not_mutate_defaults():
    """Using overrides={} must not mutate the module-level RETENTION_POLICIES."""
    original = [p.ttl_days for p in RETENTION_POLICIES]
    db = _mock_db({})
    sweep(db, dry_run=True, overrides={"LLMCall": 1})
    after = [p.ttl_days for p in RETENTION_POLICIES]
    assert original == after
