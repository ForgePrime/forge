"""RootCauseUniquenessRule — Phase F Stage F.5 work item 1 (forward-built).

Closes FORMAL_PROPERTIES_v2 P21 (Root Cause Uniqueness):
    exists! h in H: Consistent(h, Data) AND
                    forall h' != h: NOT Consistent(h', Data)

Operationally, for any Decision with type='root_cause':
- alternatives_considered MUST be a non-null JSONB array.
- The array MUST contain >=2 alternatives.
- Each alternative MUST have a `rejected_because` field with non-empty
  string content.

Without these, a "root cause" Decision is just a single hypothesis
asserted as true — which is precisely the prior-substituted reasoning
the property prohibits.

Per RuleAdapter Protocol: pure function. Reads only EvaluationContext
fields; no DB or external calls.

Input contract for EvaluationContext.artifact:
    {
        "decision_type": str,                  # 'root_cause' triggers the rule
        "alternatives_considered": list[dict] | None,
            # Each dict must have:
            #   - 'description': str (the alternative hypothesis)
            #   - 'rejected_because': str (why it doesn't survive evidence)
    }

Built ahead of F.5 deployment so the rule infrastructure is ready when
the F-phase wiring lands. Wiring into GateRegistry is per-transition
(e.g. Decision ANALYZING -> ACCEPTED for type='root_cause') and
deferred to F.5.
"""

from __future__ import annotations

from app.validation.rule_adapter import EvaluationContext, RuleAdapter, Verdict


RULE_CODE = "root_cause_uniqueness"
MIN_ALTERNATIVES = 2


class RootCauseUniquenessRule:
    """P21 closure at the validator boundary.

    Rule fires only for Decision.type='root_cause'. For other Decision
    types, returns PASS without further checks (single-responsibility:
    don't enforce P21 on non-root-cause Decisions).
    """

    rule_code: str = RULE_CODE

    def evaluate(self, ctx: EvaluationContext) -> Verdict:
        decision_type = ctx.artifact.get("decision_type") or ""

        # Skip non-root-cause Decisions: this rule only applies to that type.
        if decision_type != "root_cause":
            return Verdict(passed=True, rule_code=self.rule_code)

        alternatives = ctx.artifact.get("alternatives_considered")

        if not alternatives or not isinstance(alternatives, list):
            return Verdict(
                passed=False,
                rule_code=self.rule_code,
                reason=(
                    "P21: Decision.type='root_cause' requires "
                    f"alternatives_considered list with >={MIN_ALTERNATIVES} entries; "
                    f"got {type(alternatives).__name__}={alternatives!r}"
                ),
            )

        if len(alternatives) < MIN_ALTERNATIVES:
            return Verdict(
                passed=False,
                rule_code=self.rule_code,
                reason=(
                    f"P21: root_cause Decision requires >={MIN_ALTERNATIVES} "
                    f"alternatives_considered; got {len(alternatives)}"
                ),
            )

        # Each alternative must have a non-empty rejected_because.
        for idx, alt in enumerate(alternatives):
            if not isinstance(alt, dict):
                return Verdict(
                    passed=False,
                    rule_code=self.rule_code,
                    reason=(
                        f"P21: alternatives_considered[{idx}] must be a dict; "
                        f"got {type(alt).__name__}"
                    ),
                )
            rejected = alt.get("rejected_because")
            if not isinstance(rejected, str) or not rejected.strip():
                return Verdict(
                    passed=False,
                    rule_code=self.rule_code,
                    reason=(
                        f"P21: alternatives_considered[{idx}] missing or empty "
                        f"'rejected_because' (each alternative must explain why "
                        f"it does not survive evidence)"
                    ),
                )

        return Verdict(
            passed=True,
            rule_code=self.rule_code,
        )


# Module-level singleton; safe stateless reuse.
root_cause_uniqueness: RuleAdapter = RootCauseUniquenessRule()
