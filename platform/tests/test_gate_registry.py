"""Tests for GateRegistry — Phase A Stage A.2 exit gate.

Per PLAN_GATE_ENGINE T_{A.2}:
  T1: registry integrity — every (entity, from, to) in registry matches
      a CheckConstraint in DB schema; count matches expected.
  T2: purity — no DB / session / engine imports in gate_registry module.
  T3: regression — covered by the full pytest suite, not this file.

The state sets per entity are hardcoded here from the model
CheckConstraints as of 2026-04-25 (see app/models/<entity>.py). If a
model adds or removes a state, this test must be updated alongside
gate_registry.py — drift between registry and CheckConstraints fails
the test.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.validation import gate_registry as gr


# --- Source-of-truth state sets per entity (hardcoded from models) ---------
# Update these alongside any CheckConstraint change in app/models/<entity>.py.

EXECUTION_STATES = {
    "PROMPT_ASSEMBLED",
    "IN_PROGRESS",
    "DELIVERED",
    "VALIDATING",
    "ACCEPTED",
    "REJECTED",
    "EXPIRED",
    "FAILED",
}

TASK_STATES = {"TODO", "CLAIMING", "IN_PROGRESS", "DONE", "FAILED", "SKIPPED"}

DECISION_STATES = {"OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"}

FINDING_STATES = {"OPEN", "APPROVED", "DEFERRED", "REJECTED", "DISMISSED", "ACCEPTED"}

KEY_RESULT_STATES = {"NOT_STARTED", "IN_PROGRESS", "ACHIEVED", "MISSED"}

ORCHESTRATE_RUN_STATES = {
    "PENDING",
    "RUNNING",
    "PAUSED",
    "DONE",
    "FAILED",
    "CANCELLED",
    "BUDGET_EXCEEDED",
    "PARTIAL_FAIL",
    "INTERRUPTED",
}

PER_ENTITY_STATES = {
    "execution": EXECUTION_STATES,
    "task": TASK_STATES,
    "decision": DECISION_STATES,
    "finding": FINDING_STATES,
    "key_result": KEY_RESULT_STATES,
    "orchestrate_run": ORCHESTRATE_RUN_STATES,
}


# --- T1: registry integrity ------------------------------------------------


def test_registry_non_empty():
    """Registry is built at import time with > 0 entries."""
    assert len(gr.GATE_REGISTRY) > 0


def test_expected_counts_match_per_entity():
    """Every entity's transition count matches the declared EXPECTED_COUNTS.

    Drift here = either registry lost a transition or EXPECTED_COUNTS is
    stale; both fail the test for the operator to investigate.
    """
    for entity_type, expected_count in gr.EXPECTED_COUNTS.items():
        actual = len(gr.transitions_for(entity_type))
        assert actual == expected_count, (
            f"entity {entity_type!r}: expected {expected_count} transitions, got {actual}"
        )


def test_six_entities_registered():
    """A.2 work item: registry covers exactly 6 entities."""
    entities = {etype for (etype, _, _) in gr.GATE_REGISTRY}
    assert entities == set(PER_ENTITY_STATES.keys()), (
        f"entity-set mismatch: registry has {entities}, expected {set(PER_ENTITY_STATES)}"
    )


def test_every_to_state_is_valid_for_entity():
    """to_state of every transition is in the entity's model CheckConstraint."""
    for (entity_type, _from_state, to_state) in gr.GATE_REGISTRY:
        valid_states = PER_ENTITY_STATES[entity_type]
        assert to_state in valid_states, (
            f"unknown to_state {to_state!r} for entity {entity_type!r}; "
            f"valid={sorted(valid_states)}"
        )


def test_every_from_state_is_valid_or_init():
    """from_state is in the entity's CheckConstraint, OR is the __init__ pseudo-state.

    __init__ denotes creation (no prior state) and is intentionally outside
    the model enum. No other from_state value is permitted.
    """
    for (entity_type, from_state, _to_state) in gr.GATE_REGISTRY:
        if from_state == "__init__":
            continue
        valid_states = PER_ENTITY_STATES[entity_type]
        assert from_state in valid_states, (
            f"unknown from_state {from_state!r} for entity {entity_type!r}; "
            f"valid={sorted(valid_states)} (or __init__)"
        )


def test_init_only_appears_as_from_state():
    """__init__ pseudo-state is creation-only; never a to_state."""
    for (entity_type, _from_state, to_state) in gr.GATE_REGISTRY:
        assert to_state != "__init__", (
            f"__init__ found as to_state for entity {entity_type!r} "
            f"— that violates the creation-only convention"
        )


def test_no_self_transitions():
    """Lifecycle invariant: from_state != to_state for every entry."""
    for (entity_type, from_state, to_state) in gr.GATE_REGISTRY:
        assert from_state != to_state, (
            f"self-transition registered for {entity_type!r}: {from_state} -> {to_state}"
        )


def test_no_duplicate_transitions():
    """No duplicate (entity, from, to) triple — validated at import; here we re-assert."""
    keys = list(gr.GATE_REGISTRY)
    assert len(keys) == len(set(keys)), "duplicate transitions in registry"


# --- T1: API correctness ---------------------------------------------------


def test_lookup_rules_known_returns_empty_tuple():
    """A registered transition with no rules yet returns empty tuple."""
    rules = gr.lookup_rules("execution", "PROMPT_ASSEMBLED", "IN_PROGRESS")
    assert rules == ()


def test_lookup_rules_unknown_returns_empty_tuple():
    """An unregistered transition also returns empty tuple — caller distinguishes via is_registered()."""
    rules = gr.lookup_rules("execution", "PROMPT_ASSEMBLED", "NEVER_VALID_STATE")
    assert rules == ()


def test_is_registered_distinguishes_known_from_unknown():
    """is_registered() is the canonical predicate for transition validity."""
    assert gr.is_registered("execution", "PROMPT_ASSEMBLED", "IN_PROGRESS") is True
    assert gr.is_registered("execution", "PROMPT_ASSEMBLED", "NEVER_VALID_STATE") is False
    assert gr.is_registered("nonexistent_entity", "A", "B") is False


def test_transitions_for_returns_only_that_entity():
    """transitions_for(entity) returns exactly the pairs registered for that entity."""
    exec_pairs = gr.transitions_for("execution")
    assert len(exec_pairs) == gr.EXPECTED_COUNTS["execution"]
    # Cross-check against direct dict iteration
    direct = {
        (f, t)
        for (e, f, t) in gr.GATE_REGISTRY
        if e == "execution"
    }
    assert set(exec_pairs) == direct


def test_transitions_for_unknown_entity_returns_empty():
    """Unknown entity name → empty tuple (no exception)."""
    assert gr.transitions_for("unknown_entity_xyz") == ()


# --- T2: module purity (no DB imports) -------------------------------------


def test_module_has_no_db_imports():
    """Per A.2 work item: registry is a pure dict, no DB calls.

    Implements PLAN_GATE_ENGINE T_{A.2} T2 grep gate at the test layer
    (so it runs in pytest, not only in CI).
    """
    src_path = Path(gr.__file__)
    src = src_path.read_text(encoding="utf-8")
    # Forbidden patterns — exact-word matches to avoid false positives on
    # e.g. "sessionless" or comments containing "engine".
    forbidden_patterns = [
        re.compile(r"\bfrom\s+app\.database\b"),
        re.compile(r"\bimport\s+sqlalchemy\b"),
        re.compile(r"\bSession\s*\("),
        re.compile(r"\bcreate_engine\("),
        re.compile(r"\bsession\.(execute|query|add|commit|flush)\b"),
    ]
    for pat in forbidden_patterns:
        m = pat.search(src)
        assert m is None, (
            f"gate_registry.py contains forbidden DB pattern {pat.pattern!r}: "
            f"matched {m.group(0)!r}"
        )


# --- Determinism (P6) ------------------------------------------------------


def test_registry_is_deterministic_at_import_time():
    """Re-importing yields the same registry (no clock, no random, no env)."""
    import importlib
    importlib.reload(gr)
    snapshot1 = dict(gr.GATE_REGISTRY)
    importlib.reload(gr)
    snapshot2 = dict(gr.GATE_REGISTRY)
    assert snapshot1 == snapshot2
