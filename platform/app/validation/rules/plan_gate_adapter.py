"""PlanGateRuleAdapter — Phase A Stage A.3 wrapper.

Adapts `app.services.plan_gate.validate_plan_requirement_refs()` to the
RuleAdapter Protocol consumed by VerdictEngine.

Per PLAN_GATE_ENGINE A.3 work item 2:
    RuleAdapter wraps existing plan_gate + contract_validator without
    rewriting them.

The wrapped function is pure (no wall-clock, no rand, no network — verified
2026-04-25 via grep) so wrapping preserves Protocol purity. We do NOT
re-implement the validation logic; we only translate (EvaluationContext)
into the call shape `validate_plan_requirement_refs` expects, and translate
the violation list back into a Verdict.

Input contract for EvaluationContext.artifact:
    {
        "tasks_data": list[dict],            # Claude's plan output
        "project_has_source_docs": bool,     # whether project has SRC-NNN refs
    }

If the artifact dict is missing either key, the adapter assumes safe
defaults (empty tasks list + no source docs); empty violations means PASS.
This matches the legacy validator's behaviour on degenerate input.
"""

from __future__ import annotations

from app.services.plan_gate import validate_plan_requirement_refs
from app.validation.rule_adapter import EvaluationContext, RuleAdapter, Verdict


RULE_CODE = "plan_gate_requirement_refs"


class PlanGateRuleAdapter:
    """Wraps validate_plan_requirement_refs into the RuleAdapter Protocol."""

    rule_code: str = RULE_CODE

    def evaluate(self, ctx: EvaluationContext) -> Verdict:
        tasks_data = ctx.artifact.get("tasks_data") or []
        project_has_source_docs = bool(ctx.artifact.get("project_has_source_docs", False))

        violations = validate_plan_requirement_refs(
            tasks_data,
            project_has_source_docs=project_has_source_docs,
        )

        if not violations:
            return Verdict(passed=True, rule_code=self.rule_code)

        # Surface the first violation in `reason`; full count for triage.
        if len(violations) == 1:
            reason = f"plan_gate: {violations[0]}"
        else:
            reason = (
                f"plan_gate: {len(violations)} violations; first: {violations[0]} "
                f"(plus {len(violations) - 1} more)"
            )
        return Verdict(passed=False, rule_code=self.rule_code, reason=reason)


# Module-level singleton; safe stateless reuse.
plan_gate_rule: RuleAdapter = PlanGateRuleAdapter()
