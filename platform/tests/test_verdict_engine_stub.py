"""Tests for VerdictEngine stub — Phase A Stage A.3 skeleton.

Deterministic properties hold even for the stub:
  - empty rules → REJECTED (no evidence of passing per P6)
  - any rule returning passed=False → short-circuits to that verdict
  - all rules passing → returns composite passed=True Verdict
  - same inputs → identical Verdict (determinism / P6)
"""

from app.validation.rule_adapter import EvaluationContext, Verdict
from app.validation.verdict_engine import VerdictEngine


class _AlwaysPass:
    rule_code = "always_pass"

    def evaluate(self, ctx):
        return Verdict(passed=True, rule_code=self.rule_code)


class _AlwaysFail:
    rule_code = "always_fail"

    def evaluate(self, ctx):
        return Verdict(passed=False, rule_code=self.rule_code, reason="always fails")


def _ctx(**overrides):
    defaults = {
        "entity_type": "Decision",
        "entity_id": 1,
        "from_state": "OPEN",
        "to_state": "CLOSED",
        "artifact": {"foo": "bar"},
        "evidence": (1, 2, 3),
    }
    defaults.update(overrides)
    return EvaluationContext(**defaults)


def test_empty_rules_rejected():
    """Empty rules → REJECTED per P6 (no evidence of passing)."""
    v = VerdictEngine.evaluate(_ctx(), rules=())
    assert v.passed is False
    assert v.rule_code == "empty_rule_set"


def test_all_pass():
    """Every rule passing → composite passed=True."""
    v = VerdictEngine.evaluate(_ctx(), rules=(_AlwaysPass(), _AlwaysPass()))
    assert v.passed is True
    assert v.rule_code == "all_rules_passed"


def test_short_circuit_on_fail():
    """First failing rule short-circuits; rules after it not evaluated."""
    v = VerdictEngine.evaluate(_ctx(), rules=(_AlwaysFail(), _AlwaysPass()))
    assert v.passed is False
    assert v.rule_code == "always_fail"


def test_determinism():
    """Same inputs → same Verdict across invocations (P6)."""
    rules = (_AlwaysPass(),)
    v1 = VerdictEngine.evaluate(_ctx(), rules=rules)
    v2 = VerdictEngine.evaluate(_ctx(), rules=rules)
    v3 = VerdictEngine.evaluate(_ctx(), rules=rules)
    assert v1 == v2 == v3
