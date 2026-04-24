"""GateRegistry — Phase A Stage A.2.

Static map (entity_type, from_state, to_state) -> tuple[RuleAdapter, ...].
Purpose per FORMAL_PROPERTIES_v2 P7:
  - Enforce that state transitions only proceed through registered rule sets.
  - Disallow ad-hoc `entity.status = "X"` assignments (detected at Phase A.4
    cutover via CI grep-gate).

Shadow mode: rule tuples are empty at A.2 exit; populated progressively
per stage (A.3 wires plan_gate + contract_validator rule adapters).
Phase A.4 enforces that every (entity, from, to) transition in production
code has an entry here — empty tuple means "registered transition, no
rules yet" not "untracked transition".

Source-of-truth for the state set per entity is the CheckConstraint in
`app/models/<entity>.py`. Transitions enumerated below are the canonical
lifecycle progressions; see the entity's API handlers for the actual
sites of state change. This registry IS the single source of truth for
*permitted* transitions — anything not registered is REJECTED at Phase
A.4 enforcement.

The "__init__" pseudo-state denotes entity creation (no prior state).
Used uniformly across entities so the registry shape is dict-of-3-tuples
without optional-from semantics.

NOT exhaustive: only canonical transitions are listed. If a code path
attempts an unregistered transition, this is intentionally a Phase A.4
REJECT (the registry is the spec, not a catalog of observed behavior).
"""

from __future__ import annotations

from app.validation.rule_adapter import RuleAdapter
from app.validation.rules import evidence_link_required

# --- Per-entity transition lists -------------------------------------------
# Sources verified 2026-04-25 via grep of app/models/*.py CheckConstraints.

# Execution (8 states per app/models/execution.py:14-16):
# PROMPT_ASSEMBLED, IN_PROGRESS, DELIVERED, VALIDATING, ACCEPTED, REJECTED,
# EXPIRED, FAILED.
_EXECUTION_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("__init__", "PROMPT_ASSEMBLED"),
    ("PROMPT_ASSEMBLED", "IN_PROGRESS"),
    ("IN_PROGRESS", "DELIVERED"),
    ("DELIVERED", "VALIDATING"),
    ("VALIDATING", "ACCEPTED"),
    ("VALIDATING", "REJECTED"),
    ("IN_PROGRESS", "EXPIRED"),
    ("IN_PROGRESS", "FAILED"),
)

# Task (6 states per app/models/task.py:34): TODO, CLAIMING, IN_PROGRESS,
# DONE, FAILED, SKIPPED.
_TASK_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("__init__", "TODO"),
    ("TODO", "CLAIMING"),
    ("CLAIMING", "IN_PROGRESS"),
    ("CLAIMING", "TODO"),  # lease released without progress
    ("IN_PROGRESS", "DONE"),
    ("IN_PROGRESS", "FAILED"),
    ("IN_PROGRESS", "SKIPPED"),
)

# Decision (6 states per app/models/decision.py:13): OPEN, CLOSED, DEFERRED,
# ANALYZING, MITIGATED, ACCEPTED.
_DECISION_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("__init__", "OPEN"),
    ("OPEN", "ANALYZING"),
    ("OPEN", "DEFERRED"),
    ("DEFERRED", "OPEN"),
    ("ANALYZING", "ACCEPTED"),
    ("ACCEPTED", "CLOSED"),
    ("ANALYZING", "MITIGATED"),
    ("MITIGATED", "CLOSED"),
)

# Finding (6 states per app/models/finding.py:16): OPEN, APPROVED, DEFERRED,
# REJECTED, DISMISSED, ACCEPTED.
_FINDING_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("__init__", "OPEN"),
    ("OPEN", "APPROVED"),
    ("OPEN", "DEFERRED"),
    ("OPEN", "DISMISSED"),
    ("OPEN", "REJECTED"),
    ("APPROVED", "ACCEPTED"),
)

# KeyResult (4 states per app/models/objective.py:66): NOT_STARTED,
# IN_PROGRESS, ACHIEVED, MISSED.
_KEY_RESULT_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("__init__", "NOT_STARTED"),
    ("NOT_STARTED", "IN_PROGRESS"),
    ("IN_PROGRESS", "ACHIEVED"),
    ("IN_PROGRESS", "MISSED"),
)

# OrchestrateRun (9 states per app/models/orchestrate_run.py:19): PENDING,
# RUNNING, PAUSED, DONE, FAILED, CANCELLED, BUDGET_EXCEEDED, PARTIAL_FAIL,
# INTERRUPTED.
_ORCHESTRATE_RUN_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("__init__", "PENDING"),
    ("PENDING", "RUNNING"),
    ("RUNNING", "PAUSED"),
    ("PAUSED", "RUNNING"),
    ("RUNNING", "DONE"),
    ("RUNNING", "FAILED"),
    ("RUNNING", "BUDGET_EXCEEDED"),
    ("RUNNING", "PARTIAL_FAIL"),
    ("RUNNING", "INTERRUPTED"),
    ("RUNNING", "CANCELLED"),
    ("PAUSED", "CANCELLED"),
)


# Per-transition rule overrides. Empty tuple is the default for any
# transition not in this map — placeholder for stages A.3+ to wire rule
# adapters. Entries here are concrete rules already implemented and
# binding (Stage A.1+).
#
# Decision transitions to permanent states (ACCEPTED, CLOSED, MITIGATED)
# require >=1 EvidenceSet — closes FORMAL P16 at the state-transition
# gate. OPEN/ANALYZING/DEFERRED are work-in-progress states where
# evidence is legitimately still being collected, so no rule there.
_RULE_OVERRIDES: dict[tuple[str, str, str], tuple[RuleAdapter, ...]] = {
    ("decision", "ANALYZING", "ACCEPTED"): (evidence_link_required,),
    ("decision", "ANALYZING", "MITIGATED"): (evidence_link_required,),
    ("decision", "ACCEPTED", "CLOSED"): (evidence_link_required,),
    ("decision", "MITIGATED", "CLOSED"): (evidence_link_required,),
}


def _build_registry() -> dict[tuple[str, str, str], tuple[RuleAdapter, ...]]:
    """Construct the registry deterministically at import time.

    For each enumerated transition, look up _RULE_OVERRIDES; default to
    empty tuple (placeholder for stages that add rules later).

    Phase A.3 will bind plan_gate + contract_validator adapters as
    further per-transition entries; later stages add per-property rules
    (P12 self-adjointness at E.1, P13 invariant preservation at E.2, etc.).

    The dict is built once and frozen by tuple wrapping; runtime code
    treats GATE_REGISTRY as immutable.
    """
    out: dict[tuple[str, str, str], tuple[RuleAdapter, ...]] = {}
    for entity_type, transitions in _PER_ENTITY:
        for from_state, to_state in transitions:
            key = (entity_type, from_state, to_state)
            if key in out:
                # Defensive: duplicate registration is a programmer error.
                raise ValueError(f"duplicate transition registered: {key}")
            out[key] = _RULE_OVERRIDES.get(key, ())
    # Cross-check: every override key is a valid transition (catches typos
    # in _RULE_OVERRIDES against the canonical transition list).
    for key in _RULE_OVERRIDES:
        if key not in out:
            raise ValueError(
                f"_RULE_OVERRIDES references unregistered transition {key}; "
                f"add to the per-entity transition list first"
            )
    return out


_PER_ENTITY: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("execution", _EXECUTION_TRANSITIONS),
    ("task", _TASK_TRANSITIONS),
    ("decision", _DECISION_TRANSITIONS),
    ("finding", _FINDING_TRANSITIONS),
    ("key_result", _KEY_RESULT_TRANSITIONS),
    ("orchestrate_run", _ORCHESTRATE_RUN_TRANSITIONS),
)

# Static registry — edits require PR with ADR reference.
# Key: (entity_type, from_state, to_state) -> tuple of rules applied in order.
GATE_REGISTRY: dict[tuple[str, str, str], tuple[RuleAdapter, ...]] = _build_registry()


# Per-entity counts (declared explicitly so a regression that drops a
# transition fails the integrity test — not just the count test).
EXPECTED_COUNTS: dict[str, int] = {
    "execution": len(_EXECUTION_TRANSITIONS),
    "task": len(_TASK_TRANSITIONS),
    "decision": len(_DECISION_TRANSITIONS),
    "finding": len(_FINDING_TRANSITIONS),
    "key_result": len(_KEY_RESULT_TRANSITIONS),
    "orchestrate_run": len(_ORCHESTRATE_RUN_TRANSITIONS),
}


def lookup_rules(entity_type: str, from_state: str, to_state: str) -> tuple[RuleAdapter, ...]:
    """Return rule tuple for a state transition.

    Returns empty tuple if transition is registered (rules pending) AND if
    transition is unknown. Caller MUST distinguish via `is_registered()`:
    in enforce mode an unknown transition is REJECTED (no evidence of
    valid transition); a registered one with empty rules is allowed
    (placeholder — rules added per stage).
    """
    return GATE_REGISTRY.get((entity_type, from_state, to_state), ())


def is_registered(entity_type: str, from_state: str, to_state: str) -> bool:
    """Predicate for whether a transition is in the registry.

    True iff the (entity_type, from_state, to_state) tuple was registered
    at module load time. Use this to distinguish empty-rules-because-
    placeholder from empty-rules-because-unknown.
    """
    return (entity_type, from_state, to_state) in GATE_REGISTRY


def transitions_for(entity_type: str) -> tuple[tuple[str, str], ...]:
    """Return all (from_state, to_state) pairs registered for an entity.

    Useful for debug, dashboards, and the A.2 integrity test.
    """
    return tuple(
        (from_s, to_s)
        for (etype, from_s, to_s) in GATE_REGISTRY
        if etype == entity_type
    )
