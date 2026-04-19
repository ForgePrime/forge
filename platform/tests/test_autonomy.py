"""Unit tests for services/autonomy.py promotion + veto logic.

Autonomy ladder is a trust-building mechanism — errors here let a project
skip levels or promote without sufficient evidence. Both scenarios reduce
user confidence in the ladder ("L5 meant nothing").

Prior coverage: indirect via HTTP tests. This file tests the pure logic
directly with mocked Sessions (no DB spin-up needed).
"""
from dataclasses import dataclass, field
import datetime as dt
import pytest

from app.services.autonomy import (
    LEVELS, PROMOTION_CRITERIA, current_level, can_promote_to, promote,
    veto_check,
)


# ---------- Fake models (duck-typed for the pure logic) ----------

@dataclass
class FakeProject:
    id: int = 1
    autonomy_level: str | None = None
    autonomy_promoted_at: dt.datetime | None = None
    contract_md: str | None = None
    config: dict | None = None


# ---------- Fake Session — controls what queries return ----------

class FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **kw):
        return self

    def join(self, *a, **kw):
        return self

    def first(self):
        return self._result if not isinstance(self._result, list) else None

    def count(self):
        if isinstance(self._result, int):
            return self._result
        if isinstance(self._result, list):
            return len(self._result)
        return 0

    def all(self):
        return self._result if isinstance(self._result, list) else []


class FakeSession:
    """Dispatches queries based on the model class. Configure via .results."""

    def __init__(self):
        self.results: dict = {}
        self.committed = False

    def query(self, model):
        # Match by class name — simpler than full ORM simulation
        return FakeQuery(self.results.get(model.__name__, []))

    def commit(self):
        self.committed = True


# ---------- current_level ----------

def test_current_level_defaults_to_L1():
    assert current_level(FakeProject()) == "L1"


def test_current_level_returns_stored_level():
    assert current_level(FakeProject(autonomy_level="L3")) == "L3"


# ---------- can_promote_to — trivial rejection paths ----------

def test_can_promote_to_unknown_level_rejected():
    ok, blockers = can_promote_to(FakeSession(), FakeProject(), "L9")
    assert ok is False
    assert "unknown level" in blockers[0]


def test_can_promote_to_same_level_rejected():
    ok, blockers = can_promote_to(
        FakeSession(), FakeProject(autonomy_level="L2"), "L2",
    )
    assert ok is False
    assert "already at or above L2" in blockers[0]


def test_can_promote_to_lower_level_rejected():
    ok, blockers = can_promote_to(
        FakeSession(), FakeProject(autonomy_level="L4"), "L2",
    )
    assert ok is False
    assert "already at or above L2" in blockers[0]


def test_can_promote_to_skip_level_rejected():
    """L1 → L3 must be rejected; user must go L1→L2→L3 sequentially."""
    ok, blockers = can_promote_to(FakeSession(), FakeProject(), "L3")
    assert ok is False
    assert "cannot skip levels" in blockers[0]


# ---------- can_promote_to — criteria enforcement ----------

def test_L2_promotion_requires_nothing():
    """L2 is the starting point — zero clean runs, zero contract chars."""
    s = FakeSession()
    s.results = {"OrchestrateRun": 0, "Project": FakeProject(autonomy_level="L1")}
    ok, blockers = can_promote_to(s, FakeProject(autonomy_level="L1"), "L2")
    assert ok is True
    assert blockers == []


def test_L3_blocked_without_clean_runs():
    s = FakeSession()
    s.results = {"OrchestrateRun": 0, "Project": FakeProject(autonomy_level="L2")}
    proj = FakeProject(autonomy_level="L2", contract_md="x" * 300)
    ok, blockers = can_promote_to(s, proj, "L3")
    assert ok is False
    assert any("clean orchestrate runs" in b for b in blockers)


def test_L3_blocked_without_contract():
    s = FakeSession()
    s.results = {"OrchestrateRun": 5, "Project": FakeProject(autonomy_level="L2")}
    proj = FakeProject(autonomy_level="L2", contract_md="")
    ok, blockers = can_promote_to(s, proj, "L3")
    assert ok is False
    assert any("contract too short" in b for b in blockers)


def test_L3_happy_path():
    """3 clean runs + 200+ char contract → L3 unlocked."""
    s = FakeSession()
    s.results = {"OrchestrateRun": 3, "Project": FakeProject(autonomy_level="L2")}
    proj = FakeProject(autonomy_level="L2", contract_md="x" * 300)
    ok, blockers = can_promote_to(s, proj, "L3")
    assert ok is True
    assert blockers == []


def test_L5_requires_zero_reopens():
    """L5 gate includes "zero objective re-opens in last 30 days"."""
    s = FakeSession()
    s.results = {
        "OrchestrateRun": 30,
        "Project": FakeProject(autonomy_level="L4"),
        "ObjectiveReopen": 2,
    }
    proj = FakeProject(autonomy_level="L4", contract_md="x" * 1500)
    ok, blockers = can_promote_to(s, proj, "L5")
    assert ok is False
    assert any("re-opens" in b for b in blockers)


def test_L5_happy_path_when_stable():
    s = FakeSession()
    s.results = {
        "OrchestrateRun": 30,
        "Project": FakeProject(autonomy_level="L4"),
        "ObjectiveReopen": 0,
    }
    proj = FakeProject(autonomy_level="L4", contract_md="x" * 1500)
    ok, blockers = can_promote_to(s, proj, "L5")
    assert ok is True


# ---------- promote raises on blocked ----------

def test_promote_raises_value_error_when_blocked():
    s = FakeSession()
    s.results = {"OrchestrateRun": 0}
    proj = FakeProject(autonomy_level="L2", contract_md="")
    with pytest.raises(ValueError) as exc:
        promote(s, proj, "L3")
    assert "promotion blocked" in str(exc.value)


def test_promote_commits_and_updates_timestamp_on_success():
    s = FakeSession()
    s.results = {"OrchestrateRun": 3, "Project": FakeProject(autonomy_level="L2")}
    proj = FakeProject(autonomy_level="L2", contract_md="x" * 300)
    result = promote(s, proj, "L3")
    assert result.autonomy_level == "L3"
    assert result.autonomy_promoted_at is not None
    assert s.committed is True


# ---------- veto_check ----------

def test_veto_budget_watermark_over_80pct():
    proj = FakeProject()
    vetoes = veto_check(proj, spent_usd=8.50, cap_usd=10.00, files_touched=[])
    assert any("budget watermark" in v for v in vetoes)


def test_veto_budget_below_80pct_clean():
    proj = FakeProject()
    vetoes = veto_check(proj, spent_usd=7.90, cap_usd=10.00, files_touched=[])
    assert not any("budget" in v for v in vetoes)


def test_veto_default_flagged_paths_trigger():
    """Migrations / billing / secrets / .env are default veto paths — always veto."""
    proj = FakeProject()
    vetoes = veto_check(proj, spent_usd=0, cap_usd=10, files_touched=["migrations/v2/x.sql"])
    assert any("flagged path touched" in v for v in vetoes)
    assert any("migrations/v2/x.sql" in v for v in vetoes)


def test_veto_custom_flagged_paths_honored():
    proj = FakeProject(config={"veto_paths": ["contracts/"]})
    vetoes = veto_check(proj, spent_usd=0, cap_usd=10,
                         files_touched=["contracts/privacy.md"])
    assert any("flagged path" in v for v in vetoes)


def test_veto_clean_touched_file_no_veto():
    proj = FakeProject()
    vetoes = veto_check(proj, spent_usd=0, cap_usd=10, files_touched=["app/users.py"])
    assert vetoes == []


# ---------- PROMOTION_CRITERIA self-check ----------

def test_promotion_criteria_monotone():
    """Higher levels must demand >= criteria of lower levels."""
    prev_runs = -1
    prev_chars = -1
    for level in ["L2", "L3", "L4", "L5"]:
        crit = PROMOTION_CRITERIA[level]
        assert crit["clean_runs_required"] >= prev_runs
        assert crit["min_contract_chars"] >= prev_chars
        prev_runs = crit["clean_runs_required"]
        prev_chars = crit["min_contract_chars"]


def test_levels_list_order():
    assert LEVELS == ["L1", "L2", "L3", "L4", "L5"]
