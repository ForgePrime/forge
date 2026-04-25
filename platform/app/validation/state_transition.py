"""commit_status_transition — Phase A Stage A.4 cutover helper.

The single canonical write-path for entity.status mutations. Replaces
all 33 direct `entity.status = "X"` assignments per PLAN_GATE_ENGINE
A.4 work item 2.

Mode-aware behaviour (driven by settings.verdict_engine_mode):
- "off"     : no-op safety check; sets entity.status = target.
              Behavior identical to direct assignment. Default.
              Zero blast radius during cutover rollout.
- "shadow"  : runs GateRegistry rules in shadow_comparator pattern
              (logs divergences to verdict_divergences, does NOT block).
              Sets entity.status = target unconditionally.
- "enforce" : runs GateRegistry rules. If any rule REJECTs, raises
              StateTransitionRejected; entity.status stays unchanged.
              Caller MUST wrap in try/except if it wants to handle
              the rejection gracefully.

The helper is the SINGLE place where entity.status mutates. Once all
sites are wrapped, the pre-commit hook (CI grep) rejects any new
`.status\s*=\s*['"]` outside this module + the verdict_engine path.

Per CONTRACT §A.6: in enforce mode, a transition that's not
registered in GateRegistry is REJECTED — caller must register every
permitted transition explicitly per A.2 spec.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.validation import gate_registry as gr
from app.validation.rule_adapter import EvaluationContext
from app.validation.verdict_engine import VerdictEngine


class StateTransitionRejected(Exception):
    """Raised in enforce mode when a transition fails its gate.

    Contains the failing Verdict.rule_code + reason for caller's diagnostics.
    """

    def __init__(self, entity_type: str, from_state: str, to_state: str,
                 rule_code: str, reason: str | None):
        self.entity_type = entity_type
        self.from_state = from_state
        self.to_state = to_state
        self.rule_code = rule_code
        self.reason = reason
        super().__init__(
            f"transition {entity_type} {from_state} -> {to_state} REJECTED "
            f"by {rule_code}: {reason or '(no reason)'}"
        )


def commit_status_transition(
    entity: Any,
    *,
    entity_type: str,
    target_state: str,
    artifact: dict | None = None,
    evidence: tuple[int, ...] = (),
    mode: str | None = None,
) -> None:
    """Set entity.status = target_state through the gate machinery.

    Args:
        entity: any object with a `.status` attribute. Read for from_state;
            written to target_state on success.
        entity_type: lowercase entity type matching GateRegistry keys
            (e.g. 'execution', 'task', 'decision', 'finding',
            'orchestrate_run', 'key_result', 'objective').
        target_state: the state to transition to.
        artifact: optional dict for the EvaluationContext.artifact field
            (consumed by per-transition rules).
        evidence: optional tuple of EvidenceSet IDs (consumed by P16
            EvidenceLinkRequiredRule etc.).
        mode: override of settings.verdict_engine_mode (for tests).

    Raises:
        StateTransitionRejected: only in 'enforce' mode AND only when
            the transition's gate rules return passed=False.

    Side effect:
        Sets entity.status = target_state (always in 'off'/'shadow';
        only on PASS in 'enforce').
    """
    effective_mode = mode if mode is not None else settings.verdict_engine_mode
    from_state = getattr(entity, "status", None) or "__init__"

    if effective_mode == "off":
        # Cutover-safe default: identical behaviour to direct assignment.
        entity.status = target_state
        return

    # Build evaluation context.
    entity_id = getattr(entity, "id", 0) or 0
    ctx = EvaluationContext(
        entity_type=entity_type,
        entity_id=entity_id,
        from_state=from_state,
        to_state=target_state,
        artifact=artifact or {},
        evidence=evidence,
    )

    rules = gr.lookup_rules(entity_type, from_state, target_state)

    # Empty rules tuple is the placeholder marker — registered transition
    # with no enforcement attached. Allow it through.
    if not rules:
        # Distinguish "no rules attached" from "transition unregistered".
        if not gr.is_registered(entity_type, from_state, target_state):
            if effective_mode == "enforce":
                raise StateTransitionRejected(
                    entity_type=entity_type,
                    from_state=from_state,
                    to_state=target_state,
                    rule_code="unregistered_transition",
                    reason=(
                        f"transition not in GateRegistry; register it "
                        f"per A.2 before enforcement"
                    ),
                )
            # shadow mode: log + permit. (Logging hookup deferred to
            # a future commit since there's no execution_id available
            # at every call site.)
        # Registered with empty rules: allow through.
        entity.status = target_state
        return

    verdict = VerdictEngine.evaluate(ctx, rules=rules)
    if verdict.passed:
        entity.status = target_state
        return

    if effective_mode == "enforce":
        raise StateTransitionRejected(
            entity_type=entity_type,
            from_state=from_state,
            to_state=target_state,
            rule_code=verdict.rule_code,
            reason=verdict.reason,
        )

    # shadow mode: rule rejected but we permit anyway (log-only). The
    # divergence-logging side-channel is in shadow_comparator; for the
    # pure state-transition path the disclosure is the rule_code +
    # reason returned to caller (or just permitted silently here).
    entity.status = target_state
