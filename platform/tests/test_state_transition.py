"""Tests for commit_status_transition — Phase A Stage A.4 cutover helper."""

from __future__ import annotations

import pytest

from app.validation.state_transition import (
    StateTransitionRejected,
    commit_status_transition,
)


class _FakeEntity:
    """Bare-minimum object with .status + .id like an ORM row."""

    def __init__(self, status: str | None = None, id: int = 0):
        self.status = status
        self.id = id


# --- mode='off' (default cutover-safe) ----------------------------------


def test_off_mode_sets_status_unconditionally():
    entity = _FakeEntity(status="OPEN")
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="ACCEPTED",
        mode="off",
    )
    assert entity.status == "ACCEPTED"


def test_off_mode_no_evidence_check():
    """Even ANALYZING -> ACCEPTED (gated by evidence) passes in off mode."""
    entity = _FakeEntity(status="ANALYZING")
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="ACCEPTED",
        evidence=(),  # would fail in enforce mode
        mode="off",
    )
    assert entity.status == "ACCEPTED"


def test_off_mode_unregistered_transition_allowed():
    """Off mode permits any transition (no GateRegistry check)."""
    entity = _FakeEntity(status="ANYTHING")
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="WHATEVER",
        mode="off",
    )
    assert entity.status == "WHATEVER"


# --- mode='shadow' --------------------------------------------------------


def test_shadow_mode_permits_evidence_required_pass():
    """Evidence present -> rule passes -> status set."""
    entity = _FakeEntity(status="ANALYZING")
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="ACCEPTED",
        evidence=(101,),
        mode="shadow",
    )
    assert entity.status == "ACCEPTED"


def test_shadow_mode_permits_even_when_rule_rejects():
    """Shadow mode logs but does not block; status still set."""
    entity = _FakeEntity(status="ANALYZING")
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="ACCEPTED",
        evidence=(),  # rule rejects but shadow lets through
        mode="shadow",
    )
    assert entity.status == "ACCEPTED"


def test_shadow_mode_unregistered_transition_permitted():
    entity = _FakeEntity(status="OPEN")
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="UNREGISTERED_STATE_X",
        mode="shadow",
    )
    assert entity.status == "UNREGISTERED_STATE_X"


# --- mode='enforce' -------------------------------------------------------


def test_enforce_mode_passes_when_evidence_present():
    entity = _FakeEntity(status="ANALYZING", id=42)
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="ACCEPTED",
        evidence=(101, 102),
        mode="enforce",
    )
    assert entity.status == "ACCEPTED"


def test_enforce_mode_rejects_evidence_required_without_evidence():
    entity = _FakeEntity(status="ANALYZING", id=42)
    with pytest.raises(StateTransitionRejected) as exc_info:
        commit_status_transition(
            entity,
            entity_type="decision",
            target_state="ACCEPTED",
            evidence=(),
            mode="enforce",
        )
    assert exc_info.value.rule_code == "evidence_link_required"
    assert "P16" in (exc_info.value.reason or "")
    # Status NOT changed
    assert entity.status == "ANALYZING"


def test_enforce_mode_rejects_unregistered_transition():
    entity = _FakeEntity(status="OPEN", id=1)
    with pytest.raises(StateTransitionRejected) as exc_info:
        commit_status_transition(
            entity,
            entity_type="decision",
            target_state="NEVER_VALID",
            mode="enforce",
        )
    assert exc_info.value.rule_code == "unregistered_transition"
    assert entity.status == "OPEN"


def test_enforce_mode_passes_for_registered_transition_no_rules():
    """Transition that's in GateRegistry but has empty rules -> allow."""
    entity = _FakeEntity(status="__init__", id=1)
    # 'execution' '__init__' -> 'PROMPT_ASSEMBLED' is registered with no rules
    commit_status_transition(
        entity,
        entity_type="execution",
        target_state="PROMPT_ASSEMBLED",
        mode="enforce",
    )
    assert entity.status == "PROMPT_ASSEMBLED"


def test_enforce_mode_passes_other_decision_transitions_without_evidence():
    """Decision OPEN -> ANALYZING is registered without rules; passes."""
    entity = _FakeEntity(status="OPEN", id=1)
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="ANALYZING",
        mode="enforce",
    )
    assert entity.status == "ANALYZING"


# --- StateTransitionRejected exception structure ------------------------


def test_state_transition_rejected_carries_diagnostics():
    """Exception fields are populated for caller's logging."""
    entity = _FakeEntity(status="ANALYZING", id=42)
    try:
        commit_status_transition(
            entity,
            entity_type="decision",
            target_state="ACCEPTED",
            evidence=(),
            mode="enforce",
        )
    except StateTransitionRejected as e:
        assert e.entity_type == "decision"
        assert e.from_state == "ANALYZING"
        assert e.to_state == "ACCEPTED"
        assert e.rule_code == "evidence_link_required"
        assert e.reason is not None
        # str(e) is human-readable
        msg = str(e)
        assert "decision" in msg
        assert "ANALYZING -> ACCEPTED" in msg
        assert "REJECTED" in msg


# --- Behaviour preservation: __init__ pseudo-state -----------------------


def test_creation_uses_init_pseudo_state():
    """Entity with status=None falls back to '__init__' as from_state."""
    entity = _FakeEntity(status=None, id=0)
    # 'decision' '__init__' -> 'OPEN' is registered without rules
    commit_status_transition(
        entity,
        entity_type="decision",
        target_state="OPEN",
        mode="enforce",
    )
    assert entity.status == "OPEN"
