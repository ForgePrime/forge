"""RuleAdapter protocol — Phase A Stage A.3.

Adapts existing validators (contract_validator.py, plan_gate.py, etc.) to
the VerdictEngine rule-invocation protocol. No logic yet — interface only.

Blocked on: ADR-005 CLOSED (Invariant.check_fn format — informs adapter
signature choice between Python-callable / DSL / SQL).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Verdict:
    """Deterministic output of a rule invocation.

    Pure data; no side effects. Per P6 determinism.
    """

    passed: bool
    rule_code: str
    reason: str | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationContext:
    """Immutable context passed to every rule invocation.

    Same inputs (artifact, evidence, rules, context) → same Verdict.
    """

    entity_type: str
    entity_id: int
    from_state: str
    to_state: str
    artifact: dict  # the state-transition candidate
    evidence: tuple[int, ...]  # EvidenceSet.id references


class RuleAdapter(Protocol):
    """Protocol for a rule that can be invoked by VerdictEngine.

    Implementations must be pure functions: same context → same Verdict.
    No database writes, no external calls, no clock reads.
    """

    rule_code: str  # unique identifier, stable across versions

    def evaluate(self, ctx: EvaluationContext) -> Verdict:
        """Return deterministic Verdict for this rule on given context."""
        ...
