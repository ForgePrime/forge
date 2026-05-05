"""VerdictEngine — Phase A Stage A.3 (stub).

Per PLAN_GATE_ENGINE.md:
  - Pure function: evaluate(artifact, evidence, rules) → Verdict
  - No I/O, no clock, no random; deterministic per P6.
  - Same inputs → same output across runs (Phase D.1 T1 property test).

Shadow mode: controlled by `settings.VERDICT_ENGINE_MODE`:
  - 'off' (default): evaluate() runs but does not influence state transitions;
    comparison reports only.
  - 'shadow': evaluate() runs in parallel with legacy validators; diffs logged
    for Phase A.4 cutover calibration.
  - 'enforce': evaluate() is authoritative; legacy path removed. Activated
    at Phase A.4 per ROADMAP.

Blocked on: ADR-004 CLOSED (τ tolerance for determinism tests in D.2),
ADR-014 CLOSED (C2 sufficiency gate placement).
"""

from __future__ import annotations

from app.validation.rule_adapter import EvaluationContext, RuleAdapter, Verdict


class VerdictEngine:
    """Stateless evaluator — composes rule adapters deterministically.

    This is a stub: the contract is fixed but rule composition + precedence
    is finalized per GateRegistry in A.2.
    """

    @staticmethod
    def evaluate(ctx: EvaluationContext, rules: tuple[RuleAdapter, ...]) -> Verdict:
        """Apply every rule; return REJECTED on first failure (fail-fast).

        Deterministic: rule invocation order is the tuple order; no parallelism.
        All rules are pure; no rule raises — returns Verdict with passed=False.
        """
        if not rules:
            return Verdict(
                passed=False,
                rule_code="empty_rule_set",
                reason="no rules supplied; REJECTED by default per P6 "
                "(no rules = no evidence of passing)",
            )
        for rule in rules:
            verdict = rule.evaluate(ctx)
            if not verdict.passed:
                return verdict
        return Verdict(
            passed=True,
            rule_code="all_rules_passed",
            evidence_refs=tuple(str(e) for e in ctx.evidence),
        )
