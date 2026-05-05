"""ContractValidatorRuleAdapter — Phase A Stage A.3 wrapper.

Adapts `app.services.contract_validator.validate_delivery()` to the
RuleAdapter Protocol consumed by VerdictEngine.

Per PLAN_GATE_ENGINE A.3 work item 2:
    RuleAdapter wraps existing plan_gate + contract_validator without
    rewriting them.

The wrapped function is pure (no wall-clock, no rand, no network — verified
2026-04-25 via grep). Wrapping preserves Protocol purity.

Input contract for EvaluationContext.artifact:
    {
        "delivery": dict,                # the delivery payload to validate
        "contract": dict,                # the OutputContract fields/rules
        "task_type": str,                # 'feature' | 'bug' | etc.
        "prev_attempt": dict | None,     # optional previous-attempt context
        "ac_verifications": dict | None, # {ac_index: 'test'|'command'|'manual'}
    }

The legacy validator returns a `ValidationResult(all_pass, checks, fix_instructions)`.
We translate:
- `all_pass=True` -> Verdict(passed=True)
- `all_pass=False` -> Verdict(passed=False, reason=summary of failed checks)

The full check list is available via the wrapped function for callers
that need fine-grained diagnostics; the Verdict surfaces the highest-
severity failure for fast-path consumers.
"""

from __future__ import annotations

from app.services.contract_validator import validate_delivery
from app.validation.rule_adapter import EvaluationContext, RuleAdapter, Verdict


RULE_CODE = "contract_validator_delivery"


class ContractValidatorRuleAdapter:
    """Wraps validate_delivery into the RuleAdapter Protocol."""

    rule_code: str = RULE_CODE

    def evaluate(self, ctx: EvaluationContext) -> Verdict:
        delivery = ctx.artifact.get("delivery") or {}
        contract = ctx.artifact.get("contract") or {}
        task_type = ctx.artifact.get("task_type") or "feature"
        prev_attempt = ctx.artifact.get("prev_attempt")
        ac_verifications = ctx.artifact.get("ac_verifications")

        result = validate_delivery(
            delivery=delivery,
            contract=contract,
            task_type=task_type,
            prev_attempt=prev_attempt,
            ac_verifications=ac_verifications,
        )

        if result.all_pass:
            return Verdict(passed=True, rule_code=self.rule_code)

        # Summarize first FAIL check for the verdict reason; full check list
        # remains accessible via direct contract_validator invocation for
        # callers that need triage detail.
        failed = [c for c in result.checks if c.status == "FAIL"]
        if not failed:
            # all_pass=False but no FAIL checks — defensive (shouldn't happen
            # given current validator implementation, but the Protocol must
            # behave deterministically for unexpected inputs).
            reason = "contract_validator: failed without specific checks"
        elif len(failed) == 1:
            f = failed[0]
            reason = f"contract_validator: {f.check}: {f.detail or 'failed'}"
        else:
            f = failed[0]
            reason = (
                f"contract_validator: {len(failed)} FAIL checks; first: "
                f"{f.check}: {f.detail or 'failed'} "
                f"(plus {len(failed) - 1} more)"
            )
        return Verdict(passed=False, rule_code=self.rule_code, reason=reason)


# Module-level singleton; safe stateless reuse.
contract_validator_rule: RuleAdapter = ContractValidatorRuleAdapter()
