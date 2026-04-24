"""EvidenceLinkRequiredRule — Phase A Stage A.1 work item 4.

Closes FORMAL_PROPERTIES_v2 P16 (evidence existence) at the state-transition
gate level: a Decision cannot transition into a permanent state (ACCEPTED,
CLOSED, MITIGATED — the states where the Decision is acted upon downstream)
without at least one linked EvidenceSet row.

Rationale for state-transition gating (vs DB-level NOT NULL on Decision):
- Decision.id is the FK target for EvidenceSet.decision_id; insert order
  forces Decision-first, then EvidenceSet, so a NOT NULL constraint on
  Decision pointing back to EvidenceSet creates a chicken-and-egg.
- State-transition gating at ACCEPTED/CLOSED/MITIGATED matches FORMAL P16's
  acceptance signal ("zero ACCEPTED Decisions with no evidence edge"); the
  OPEN/ANALYZING/DEFERRED states are work-in-progress where evidence is
  legitimately still being collected.

Per FORMAL_PROPERTIES_v2 P16:
    forall d in Decisions: d valid => exists E(d) != empty

Per RuleAdapter Protocol: pure function. The EvaluationContext.evidence
tuple is the source of truth — caller is responsible for populating it
with the EvidenceSet IDs in the same transaction. The rule does NOT query
the DB; that would violate the Protocol's purity requirement.
"""

from __future__ import annotations

from app.validation.rule_adapter import EvaluationContext, RuleAdapter, Verdict


RULE_CODE = "evidence_link_required"


class EvidenceLinkRequiredRule:
    """Reject if context has zero linked EvidenceSet rows.

    Stateless; safe to instantiate once and reuse (the singleton
    `evidence_link_required` below is the canonical instance).
    """

    rule_code: str = RULE_CODE

    def evaluate(self, ctx: EvaluationContext) -> Verdict:
        if len(ctx.evidence) >= 1:
            return Verdict(
                passed=True,
                rule_code=self.rule_code,
                evidence_refs=tuple(str(e) for e in ctx.evidence),
            )
        return Verdict(
            passed=False,
            rule_code=self.rule_code,
            reason=(
                f"transition {ctx.entity_type} {ctx.from_state}->{ctx.to_state} "
                f"requires >=1 EvidenceSet link (P16); none provided"
            ),
        )


# Module-level singleton — registered in GateRegistry without per-call
# instantiation overhead. Pure stateless object; safe to share.
evidence_link_required: RuleAdapter = EvidenceLinkRequiredRule()
