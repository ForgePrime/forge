"""Tests for plan_gate + contract_validator RuleAdapter wrappers — Phase A.3.

Exercises the Protocol translation layer over existing pure validators.
Does NOT re-test the underlying validator logic (that's covered by their
own existing tests); only that:

1. The wrapper extracts the right fields from EvaluationContext.artifact.
2. PASS / FAIL translates correctly to Verdict shape.
3. The reason string surfaces the first failing check (or the violation).
4. Determinism (P6) holds — same context -> same Verdict.
5. VerdictEngine + adapter compose end-to-end.

Reference: existing tests for the underlying validators live in
test_contract_validator_gates.py and the plan_gate test fixtures in
test_chunks_*.py.
"""

from __future__ import annotations

from app.validation.rule_adapter import EvaluationContext, Verdict
from app.validation.rules import (
    contract_validator_rule,
    plan_gate_rule,
)
from app.validation.verdict_engine import VerdictEngine


def _ctx(artifact: dict, **overrides) -> EvaluationContext:
    defaults = {
        "entity_type": "execution",
        "entity_id": 1,
        "from_state": "PROMPT_ASSEMBLED",
        "to_state": "IN_PROGRESS",
        "artifact": artifact,
        "evidence": (),
    }
    defaults.update(overrides)
    return EvaluationContext(**defaults)


# --- PlanGateRuleAdapter ---------------------------------------------------


def test_plan_gate_passes_when_no_source_docs():
    """No source docs => plan_gate is a no-op => PASS."""
    artifact = {
        "tasks_data": [{"type": "feature", "external_id": "T-001"}],
        "project_has_source_docs": False,
    }
    v = plan_gate_rule.evaluate(_ctx(artifact))
    assert v.passed is True
    assert v.rule_code == "plan_gate_requirement_refs"


def test_plan_gate_passes_with_well_formed_refs():
    """Source docs present + refs well-formed => PASS."""
    artifact = {
        "tasks_data": [
            {"type": "feature", "external_id": "T-001",
             "requirement_refs": ["SRC-001 §2.4", "SRC-002"]},
        ],
        "project_has_source_docs": True,
    }
    v = plan_gate_rule.evaluate(_ctx(artifact))
    assert v.passed is True


def test_plan_gate_rejects_missing_refs():
    """Source docs present but feature task has no refs => FAIL."""
    artifact = {
        "tasks_data": [
            {"type": "feature", "external_id": "T-001"},  # no requirement_refs
        ],
        "project_has_source_docs": True,
    }
    v = plan_gate_rule.evaluate(_ctx(artifact))
    assert v.passed is False
    assert v.rule_code == "plan_gate_requirement_refs"
    assert "T-001" in (v.reason or "")
    assert "requirement_refs" in (v.reason or "")


def test_plan_gate_rejects_malformed_refs():
    """Refs present but malformed (don't match SRC-NNN regex) => FAIL."""
    artifact = {
        "tasks_data": [
            {"type": "feature", "external_id": "T-001",
             "requirement_refs": ["not-a-valid-token", ""]},
        ],
        "project_has_source_docs": True,
    }
    v = plan_gate_rule.evaluate(_ctx(artifact))
    assert v.passed is False
    assert "malformed" in (v.reason or "").lower()


def test_plan_gate_summarizes_multi_violation():
    """Multiple violations => reason names first + count of remainder."""
    artifact = {
        "tasks_data": [
            {"type": "feature", "external_id": "T-001"},
            {"type": "bug", "external_id": "T-002"},
            {"type": "develop", "external_id": "T-003"},
        ],
        "project_has_source_docs": True,
    }
    v = plan_gate_rule.evaluate(_ctx(artifact))
    assert v.passed is False
    assert "3 violations" in (v.reason or "")
    assert "plus 2 more" in (v.reason or "")


def test_plan_gate_skips_non_required_task_types():
    """chore/investigation tasks may legitimately omit refs."""
    artifact = {
        "tasks_data": [
            {"type": "chore", "external_id": "T-001"},
            {"type": "investigation", "external_id": "T-002"},
        ],
        "project_has_source_docs": True,
    }
    v = plan_gate_rule.evaluate(_ctx(artifact))
    assert v.passed is True


def test_plan_gate_handles_missing_artifact_keys():
    """Defensive: artifact without expected keys => safe defaults => PASS."""
    v = plan_gate_rule.evaluate(_ctx(artifact={}))
    assert v.passed is True


def test_plan_gate_determinism():
    """Same input => same Verdict (P6)."""
    artifact = {
        "tasks_data": [
            {"type": "feature", "external_id": "T-001",
             "requirement_refs": ["SRC-001"]},
        ],
        "project_has_source_docs": True,
    }
    v1 = plan_gate_rule.evaluate(_ctx(artifact))
    v2 = plan_gate_rule.evaluate(_ctx(artifact))
    v3 = plan_gate_rule.evaluate(_ctx(artifact))
    assert v1 == v2 == v3


# --- ContractValidatorRuleAdapter ------------------------------------------
# Using minimal contracts to exercise the adapter's translation layer
# without dragging in the full delivery test fixtures.


def _minimal_contract() -> dict:
    """Minimal OutputContract that requires reasoning of >=10 chars."""
    return {
        "required": {
            "reasoning": {"min_length": 10},
        },
    }


def test_contract_validator_passes_with_chore_task_type():
    """task_type='chore' skips operational requirements => PASS on minimal."""
    artifact = {
        "delivery": {"reasoning": "this is a sufficiently long reasoning"},
        "contract": _minimal_contract(),
        "task_type": "chore",
    }
    v = contract_validator_rule.evaluate(_ctx(artifact))
    assert v.passed is True
    assert v.rule_code == "contract_validator_delivery"


def test_contract_validator_rejects_short_reasoning():
    """Reasoning under min_length => FAIL."""
    artifact = {
        "delivery": {"reasoning": "short"},
        "contract": _minimal_contract(),
        "task_type": "feature",
    }
    v = contract_validator_rule.evaluate(_ctx(artifact))
    assert v.passed is False
    assert v.rule_code == "contract_validator_delivery"
    assert "reasoning" in (v.reason or "").lower()


def test_contract_validator_handles_missing_artifact_keys():
    """Defensive: missing artifact keys => safe defaults => task_type='feature'
    triggers operational checks => FAIL with structured reason.

    The adapter does NOT fail-closed on missing inputs (legacy validator
    behaviour preserved); it dispatches to the validator which then fails
    feature/bug task types for missing operational fields. Adapter
    returns a well-formed FAIL Verdict — that's the integration contract.
    """
    v = contract_validator_rule.evaluate(_ctx(artifact={}))
    assert v.passed is False
    assert v.rule_code == "contract_validator_delivery"
    # Reason must surface the first FAIL check (some operational rule).
    assert v.reason and "contract_validator" in v.reason


def test_contract_validator_determinism():
    """Same input => same Verdict (P6)."""
    artifact = {
        "delivery": {"reasoning": "x"},
        "contract": _minimal_contract(),
        "task_type": "feature",
    }
    v1 = contract_validator_rule.evaluate(_ctx(artifact))
    v2 = contract_validator_rule.evaluate(_ctx(artifact))
    assert v1 == v2


# --- VerdictEngine integration ---------------------------------------------


def test_verdict_engine_runs_plan_gate_adapter_pass():
    rules = (plan_gate_rule,)
    artifact = {
        "tasks_data": [{"type": "feature", "external_id": "T-001",
                        "requirement_refs": ["SRC-001"]}],
        "project_has_source_docs": True,
    }
    v = VerdictEngine.evaluate(_ctx(artifact), rules=rules)
    assert v.passed is True
    assert v.rule_code == "all_rules_passed"


def test_verdict_engine_runs_plan_gate_adapter_fail():
    rules = (plan_gate_rule,)
    artifact = {
        "tasks_data": [{"type": "feature", "external_id": "T-001"}],
        "project_has_source_docs": True,
    }
    v = VerdictEngine.evaluate(_ctx(artifact), rules=rules)
    assert v.passed is False
    assert v.rule_code == "plan_gate_requirement_refs"


def test_verdict_engine_composes_multiple_adapters():
    """Multiple rules in tuple — engine evaluates in order, fail-fast."""
    rules = (plan_gate_rule, contract_validator_rule)
    # Plan PASSES, contract FAILS — VerdictEngine must surface contract FAIL.
    artifact = {
        "tasks_data": [],  # empty = plan_gate returns PASS
        "project_has_source_docs": True,
        "delivery": {"reasoning": "x"},  # too short
        "contract": _minimal_contract(),
        "task_type": "feature",
    }
    v = VerdictEngine.evaluate(_ctx(artifact), rules=rules)
    assert v.passed is False
    assert v.rule_code == "contract_validator_delivery"


def test_verdict_engine_short_circuits_on_first_fail():
    """Plan FAILS first — contract_validator is NOT evaluated."""
    rules = (plan_gate_rule, contract_validator_rule)
    artifact = {
        "tasks_data": [{"type": "feature", "external_id": "T-001"}],  # no refs
        "project_has_source_docs": True,
        # contract intentionally missing — would crash if called, but
        # plan_gate fails first so contract_validator never runs.
    }
    v = VerdictEngine.evaluate(_ctx(artifact), rules=rules)
    assert v.passed is False
    assert v.rule_code == "plan_gate_requirement_refs"
