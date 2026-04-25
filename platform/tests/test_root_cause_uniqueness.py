"""Tests for RootCauseUniquenessRule — Phase F Stage F.5 (P21).

Pure-Python tests; no DB. Cover:
- Non-root-cause Decisions: rule is no-op (returns PASS).
- Root-cause Decision missing alternatives_considered: REJECT.
- Root-cause with <2 alternatives: REJECT.
- Root-cause with 2+ alternatives but missing rejected_because: REJECT.
- Root-cause with 2+ alternatives all properly rejected: PASS.
- Determinism (P6).
"""

from __future__ import annotations

from app.validation.rule_adapter import EvaluationContext
from app.validation.rules import RootCauseUniquenessRule, root_cause_uniqueness


def _ctx(artifact: dict) -> EvaluationContext:
    return EvaluationContext(
        entity_type="decision",
        entity_id=1,
        from_state="ANALYZING",
        to_state="ACCEPTED",
        artifact=artifact,
        evidence=(),
    )


# --- Non-root-cause Decisions: rule is no-op ------------------------------


def test_non_root_cause_decision_passes():
    """For decision_type != 'root_cause', the rule does not fire."""
    v = root_cause_uniqueness.evaluate(_ctx({"decision_type": "operational"}))
    assert v.passed is True
    assert v.rule_code == "root_cause_uniqueness"


def test_missing_decision_type_treated_as_non_root_cause():
    """Empty artifact (no decision_type) -> rule does not fire -> PASS."""
    v = root_cause_uniqueness.evaluate(_ctx({}))
    assert v.passed is True


def test_other_decision_types_pass_regardless_of_alternatives():
    """Even with empty alternatives_considered, non-root-cause types PASS."""
    artifact = {
        "decision_type": "architectural",
        "alternatives_considered": [],
    }
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is True


# --- Root-cause Decisions: rule enforces P21 ------------------------------


def test_root_cause_missing_alternatives_rejected():
    """Root-cause without alternatives_considered field -> REJECT."""
    v = root_cause_uniqueness.evaluate(_ctx({"decision_type": "root_cause"}))
    assert v.passed is False
    assert v.rule_code == "root_cause_uniqueness"
    assert "P21" in (v.reason or "")
    assert "alternatives_considered" in (v.reason or "")


def test_root_cause_null_alternatives_rejected():
    artifact = {"decision_type": "root_cause", "alternatives_considered": None}
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is False


def test_root_cause_empty_alternatives_rejected():
    artifact = {"decision_type": "root_cause", "alternatives_considered": []}
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is False
    assert "P21" in (v.reason or "")


def test_root_cause_one_alternative_rejected():
    """1 alternative is not enough — P21 requires >=2."""
    artifact = {
        "decision_type": "root_cause",
        "alternatives_considered": [
            {"description": "DB lock contention", "rejected_because": "..."},
        ],
    }
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is False
    assert ">=2" in (v.reason or "") or "2" in (v.reason or "")


def test_root_cause_two_alternatives_one_missing_rejected_because():
    """If any alternative lacks rejected_because, the whole Decision REJECTed."""
    artifact = {
        "decision_type": "root_cause",
        "alternatives_considered": [
            {"description": "DB lock", "rejected_because": "no locks observed"},
            {"description": "GC pause"},  # missing rejected_because
        ],
    }
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is False
    assert "rejected_because" in (v.reason or "")
    assert "[1]" in (v.reason or "")  # surfaces which alternative


def test_root_cause_two_alternatives_with_empty_rejected_because():
    """Empty string in rejected_because is not a valid rejection reason."""
    artifact = {
        "decision_type": "root_cause",
        "alternatives_considered": [
            {"description": "A", "rejected_because": "valid"},
            {"description": "B", "rejected_because": "  "},  # whitespace only
        ],
    }
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is False


def test_root_cause_alternative_not_a_dict_rejected():
    """Alternative entries must be dicts; strings/None get clean error."""
    artifact = {
        "decision_type": "root_cause",
        "alternatives_considered": [
            {"description": "A", "rejected_because": "ok"},
            "this is not a dict",
        ],
    }
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is False
    assert "must be a dict" in (v.reason or "")


def test_root_cause_two_proper_alternatives_passes():
    """2 alternatives, both with non-empty rejected_because -> PASS."""
    artifact = {
        "decision_type": "root_cause",
        "alternatives_considered": [
            {
                "description": "DB lock contention",
                "rejected_because": "pg_locks query during incident showed no waits",
            },
            {
                "description": "Network partition between app and DB",
                "rejected_because": "TCP retransmit metrics flat throughout window",
            },
        ],
    }
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is True
    assert v.rule_code == "root_cause_uniqueness"


def test_root_cause_three_proper_alternatives_passes():
    """More than 2 alternatives also pass — minimum is 2, no maximum."""
    artifact = {
        "decision_type": "root_cause",
        "alternatives_considered": [
            {"description": "A", "rejected_because": "evidence A"},
            {"description": "B", "rejected_because": "evidence B"},
            {"description": "C", "rejected_because": "evidence C"},
        ],
    }
    v = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v.passed is True


# --- Determinism (P6) ------------------------------------------------------


def test_determinism():
    artifact = {
        "decision_type": "root_cause",
        "alternatives_considered": [
            {"description": "A", "rejected_because": "x"},
            {"description": "B", "rejected_because": "y"},
        ],
    }
    v1 = root_cause_uniqueness.evaluate(_ctx(artifact))
    v2 = root_cause_uniqueness.evaluate(_ctx(artifact))
    v3 = root_cause_uniqueness.evaluate(_ctx(artifact))
    assert v1 == v2 == v3


def test_class_can_be_instantiated_independently():
    """Class is constructible (not just module singleton)."""
    rule = RootCauseUniquenessRule()
    v = rule.evaluate(_ctx({"decision_type": "operational"}))
    assert v.passed is True
