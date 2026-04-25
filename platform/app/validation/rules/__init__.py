"""Concrete RuleAdapter implementations.

Per PLAN_GATE_ENGINE Stage A.1+, this package holds the rules that
VerdictEngine composes via GateRegistry. Each rule is a pure function
(same context -> same Verdict) per FORMAL_PROPERTIES_v2 P6.

Rules are deliberately small (single-responsibility) so the registry
composition is the place to read what a transition requires.
"""

from app.validation.rules.evidence_link_required import (
    EvidenceLinkRequiredRule,
    evidence_link_required,
)
from app.validation.rules.plan_gate_adapter import (
    PlanGateRuleAdapter,
    plan_gate_rule,
)
from app.validation.rules.contract_validator_adapter import (
    ContractValidatorRuleAdapter,
    contract_validator_rule,
)

__all__ = [
    "EvidenceLinkRequiredRule",
    "evidence_link_required",
    "PlanGateRuleAdapter",
    "plan_gate_rule",
    "ContractValidatorRuleAdapter",
    "contract_validator_rule",
]
