"""Tests for EvidenceLinkRequiredRule + GateRegistry wiring.

Phase A Stage A.1 work item 4 closure: Decision state transitions
into permanent states (ACCEPTED, CLOSED, MITIGATED) require >=1
linked EvidenceSet. Closes FORMAL_PROPERTIES_v2 P16 at the gate.
"""

from __future__ import annotations

from app.validation import gate_registry as gr
from app.validation.rule_adapter import EvaluationContext, Verdict
from app.validation.rules import EvidenceLinkRequiredRule, evidence_link_required


def _ctx(evidence: tuple[int, ...] = (), **overrides) -> EvaluationContext:
    defaults = {
        "entity_type": "decision",
        "entity_id": 1,
        "from_state": "ANALYZING",
        "to_state": "ACCEPTED",
        "artifact": {"recommendation": "rebuild the index"},
        "evidence": evidence,
    }
    defaults.update(overrides)
    return EvaluationContext(**defaults)


# --- Rule semantics --------------------------------------------------------


def test_empty_evidence_rejected():
    """Zero linked EvidenceSet rows -> REJECTED."""
    v = evidence_link_required.evaluate(_ctx(evidence=()))
    assert v.passed is False
    assert v.rule_code == "evidence_link_required"
    assert "P16" in (v.reason or "")
    assert "ANALYZING" in (v.reason or "")
    assert "ACCEPTED" in (v.reason or "")


def test_single_evidence_passes():
    """One linked EvidenceSet row -> PASSED."""
    v = evidence_link_required.evaluate(_ctx(evidence=(42,)))
    assert v.passed is True
    assert v.rule_code == "evidence_link_required"
    assert v.evidence_refs == ("42",)


def test_multiple_evidence_passes():
    """Many linked EvidenceSets -> PASSED; all IDs surfaced as evidence_refs."""
    v = evidence_link_required.evaluate(_ctx(evidence=(1, 2, 3, 4, 5)))
    assert v.passed is True
    assert v.evidence_refs == ("1", "2", "3", "4", "5")


def test_determinism():
    """Same context -> same Verdict across calls (P6)."""
    ctx = _ctx(evidence=(7, 11))
    v1 = evidence_link_required.evaluate(ctx)
    v2 = evidence_link_required.evaluate(ctx)
    v3 = evidence_link_required.evaluate(ctx)
    assert v1 == v2 == v3


def test_rule_code_is_stable_string():
    """rule_code is a stable string identifier (Protocol contract)."""
    assert isinstance(evidence_link_required.rule_code, str)
    assert evidence_link_required.rule_code == "evidence_link_required"


def test_rule_class_can_be_instantiated_independently():
    """Class is constructible (not just module singleton)."""
    rule = EvidenceLinkRequiredRule()
    v = rule.evaluate(_ctx(evidence=()))
    assert v.passed is False
    assert v.rule_code == "evidence_link_required"


# --- GateRegistry wiring ---------------------------------------------------


# The 4 decision transitions that require evidence. Hardcoded to detect
# drift if the override table changes silently.
EVIDENCE_REQUIRED_DECISION_TRANSITIONS = [
    ("decision", "ANALYZING", "ACCEPTED"),
    ("decision", "ANALYZING", "MITIGATED"),
    ("decision", "ACCEPTED", "CLOSED"),
    ("decision", "MITIGATED", "CLOSED"),
]


def test_decision_to_accepted_has_evidence_rule():
    """ANALYZING -> ACCEPTED carries EvidenceLinkRequiredRule (among others)."""
    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")
    rule_codes = {r.rule_code for r in rules}
    assert "evidence_link_required" in rule_codes


def test_all_4_evidence_required_transitions_have_rule():
    """All 4 enumerated decision transitions carry the evidence rule.

    Other rules may also be wired (e.g. root_cause_uniqueness from F.5);
    assertion is on presence of evidence_link_required, not exclusivity.
    """
    for entity, from_s, to_s in EVIDENCE_REQUIRED_DECISION_TRANSITIONS:
        rules = gr.lookup_rules(entity, from_s, to_s)
        rule_codes = {r.rule_code for r in rules}
        assert "evidence_link_required" in rule_codes, (
            f"{entity} {from_s}->{to_s}: missing evidence_link_required rule"
        )


def test_open_to_analyzing_has_no_rule():
    """OPEN -> ANALYZING is work-in-progress; no evidence rule yet (correct)."""
    rules = gr.lookup_rules("decision", "OPEN", "ANALYZING")
    assert rules == ()


def test_open_to_deferred_has_no_rule():
    """OPEN -> DEFERRED is also work-in-progress; no evidence rule (correct)."""
    rules = gr.lookup_rules("decision", "OPEN", "DEFERRED")
    assert rules == ()


def test_init_to_open_has_no_rule():
    """Decision creation (__init__ -> OPEN) is pre-evidence; no rule."""
    rules = gr.lookup_rules("decision", "__init__", "OPEN")
    assert rules == ()


def test_other_entities_decision_transitions_have_no_rule():
    """The rule is decision-specific; other entities' transitions unaffected."""
    rules = gr.lookup_rules("execution", "PROMPT_ASSEMBLED", "IN_PROGRESS")
    assert rules == ()
    rules = gr.lookup_rules("task", "TODO", "CLAIMING")
    assert rules == ()


# --- Integration with VerdictEngine ----------------------------------------


def test_verdict_engine_runs_evidence_rule_and_rejects_empty():
    """End-to-end: VerdictEngine + GateRegistry + rule produces correct verdict."""
    from app.validation.verdict_engine import VerdictEngine

    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")
    v = VerdictEngine.evaluate(_ctx(evidence=()), rules=rules)
    assert v.passed is False
    assert v.rule_code == "evidence_link_required"


def test_verdict_engine_runs_evidence_rule_and_passes_with_evidence():
    """End-to-end: with evidence linked, VerdictEngine returns PASS."""
    from app.validation.verdict_engine import VerdictEngine

    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")
    v = VerdictEngine.evaluate(_ctx(evidence=(101, 102)), rules=rules)
    assert v.passed is True
    assert v.rule_code == "all_rules_passed"
