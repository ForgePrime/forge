"""GateRegistry — Phase A Stage A.2.

Static map (entity_type, from_state, to_state) → tuple[RuleAdapter, ...].
Purpose per FORMAL_PROPERTIES_v2 P7:
  - Enforce that state transitions only proceed through registered rule sets.
  - Disallow ad-hoc `entity.status = "X"` assignments (detected at Phase A.4
    cutover via CI grep-gate).

Shadow mode: dict is empty at A.2 exit; populated progressively per
stage. Phase A.4 enforces that every (entity, from, to) transition in
production code has an entry here.
"""

from __future__ import annotations

from app.validation.rule_adapter import RuleAdapter


# Static registry — edits require PR with ADR reference.
# Key: (entity_type, from_state, to_state) → tuple of rules applied in order.
GATE_REGISTRY: dict[tuple[str, str, str], tuple[RuleAdapter, ...]] = {}


def lookup_rules(entity_type: str, from_state: str, to_state: str) -> tuple[RuleAdapter, ...]:
    """Return rule tuple for a state transition.

    Returns empty tuple if transition is not registered. Caller semantics:
    empty tuple + enforce mode → REJECTED (no evidence of valid transition).
    """
    return GATE_REGISTRY.get((entity_type, from_state, to_state), ())
