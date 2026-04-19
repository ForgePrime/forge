"""Direct contract tests for contract_validator trust gates.

Existing tests (test_p5_validator_per_ac.py, test_post_accept_branch.py) cover
COMMAND_PATTERN and per-AC evidence matching. This file fills three gates that
weren't directly asserted:

1. Confabulation check — reasoning without [EXECUTED]/[INFERRED]/[ASSUMED] tags
   must produce WARNING (gate against fluent wrongness per CGAID pathology 2.1).
2. AC composition gate — feature/bug with no PASS on negative/edge_case must FAIL
   (gate against happy-path-only per CGAID pathology 2.4).
3. Operational contract fields — feature/bug missing `assumptions` or
   `impact_analysis` must FAIL (gate against assumption-in-place-of-verification
   per CGAID 7 disclosure behaviors).

These are the mechanical enforcement points of the 3 epistemic states. If a
regression silently passes any of them, AI output could go DONE while lying.
"""
from app.services.contract_validator import validate_delivery


_MINIMAL_CONTRACT = {
    "required": {
        "reasoning": {"min_length": 50},
        "ac_evidence": {"min_length": 20},  # needed for composition gate to run
    },
    "optional": {},
    "anti_patterns": {},
}


def _base_delivery(**overrides):
    """Produce a minimal passing-structure delivery; tests override the parts under test."""
    base = {
        "reasoning": (
            "[EXECUTED] ran pytest and saw 3 passes. "
            "[INFERRED] read auth.py and concluded JWT used. "
            "[ASSUMED] bcrypt cost factor 12 is fine for our load."
        ),
        "changes": [{"file_path": "app/x.py", "action": "add", "summary": "new endpoint"}],
        "completion_claims": {"executed": [], "not_executed": []},
        "ac_evidence": [
            {
                "ac_index": 0, "verdict": "PASS", "scenario_type": "positive",
                "evidence": "[EXECUTED] GET /x returned 200 with body {id:1}",
            },
            {
                "ac_index": 1, "verdict": "PASS", "scenario_type": "negative",
                "evidence": "[EXECUTED] POST /x with bad body returned 422",
            },
        ],
        "assumptions": [{"text": "auth is JWT-based", "confidence": "HIGH"}],
        "impact_analysis": {"files_changed": ["app/x.py"], "risk": "low"},
    }
    base.update(overrides)
    return base


# ---------- Gate 1: confabulation tags ----------

def test_reasoning_without_epistemic_tags_warns():
    """The 3 epistemic tags gate. Missing tags → WARNING on feature/bug."""
    delivery = _base_delivery(reasoning=(
        "I ran the tests and they passed. I read the code and JWT is used. "
        "bcrypt is probably fine for our load; no specific data checked."
    ))
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    check_names = [c.check for c in result.checks]
    # The warning surfaces on "confabulation.no_tags"
    no_tags_checks = [c for c in result.checks if c.check == "confabulation.no_tags"]
    assert no_tags_checks, f"Expected confabulation.no_tags check; got: {check_names}"
    assert no_tags_checks[0].status == "WARNING"


def test_reasoning_with_tags_no_confabulation_warning():
    delivery = _base_delivery()  # base reasoning has all 3 tags
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    no_tags_checks = [c for c in result.checks if c.check == "confabulation.no_tags"]
    assert not no_tags_checks, "Unexpected no_tags warning when all 3 tags present"


def test_reasoning_with_only_one_tag_passes_confabulation():
    """Gate requires ANY of the 3 tags, not all three. Single [EXECUTED] counts."""
    delivery = _base_delivery(reasoning=(
        "Minimal reasoning. [EXECUTED] ran the test suite and saw it green. "
        "That is sufficient for this task."
    ))
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    no_tags_checks = [c for c in result.checks if c.check == "confabulation.no_tags"]
    assert not no_tags_checks


def test_chore_task_confabulation_check_skipped():
    """chore/investigation are exempt from the tag gate — lower ceremony."""
    delivery = _base_delivery(reasoning="Just did the cleanup.")
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "chore")
    no_tags_checks = [c for c in result.checks if c.check == "confabulation.no_tags"]
    assert not no_tags_checks, "chore should not run the confabulation gate"


# ---------- Gate 2: AC composition (negative/edge_case must PASS) ----------

def test_feature_with_only_positive_ac_fails():
    """feature with all positive AC PASS but no negative/edge_case → FAIL."""
    delivery = _base_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS", "scenario_type": "positive",
         "evidence": "[EXECUTED] test ran"},
        {"ac_index": 1, "verdict": "PASS", "scenario_type": "positive",
         "evidence": "[EXECUTED] test ran"},
    ])
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    comp_checks = [c for c in result.checks if c.check == "ac_composition"]
    assert comp_checks
    assert comp_checks[0].status == "FAIL"


def test_feature_with_edge_case_pass_satisfies_composition():
    """Single edge_case with PASS verdict satisfies the gate."""
    delivery = _base_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS", "scenario_type": "positive",
         "evidence": "[EXECUTED] happy test"},
        {"ac_index": 1, "verdict": "PASS", "scenario_type": "edge_case",
         "evidence": "[EXECUTED] boundary test"},
    ])
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    comp_checks = [c for c in result.checks if c.check == "ac_composition"]
    assert comp_checks[0].status == "PASS"


def test_feature_with_negative_fail_does_not_satisfy_composition():
    """A FAIL verdict doesn't count — only PASS on negative/edge_case passes the gate.

    Semantic: the negative scenario must be successfully handled (return error as
    expected), not the test itself failing.
    """
    delivery = _base_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS", "scenario_type": "positive",
         "evidence": "[EXECUTED] happy"},
        {"ac_index": 1, "verdict": "FAIL", "scenario_type": "negative",
         "evidence": "[EXECUTED] expected 422 got 500"},
    ])
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    comp_checks = [c for c in result.checks if c.check == "ac_composition"]
    assert comp_checks[0].status == "FAIL"


def test_chore_ac_composition_exempt():
    """chore tasks are exempt from ac_composition gate (less ceremony)."""
    delivery = _base_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS", "scenario_type": "positive",
         "evidence": "[EXECUTED]"},
    ])
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "chore")
    # No ac_composition check raised at all for chore
    comp_checks = [c for c in result.checks if c.check == "ac_composition"]
    # Contract varies — either absent or explicitly PASS. Either is acceptable.
    for c in comp_checks:
        assert c.status != "FAIL", "chore should never FAIL on ac_composition"


# ---------- Gate 3: Operational contract fields ----------

def test_feature_missing_assumptions_fails():
    delivery = _base_delivery()
    delivery.pop("assumptions")
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    assum_checks = [c for c in result.checks if c.check == "operational.assumptions"]
    assert assum_checks
    assert assum_checks[0].status == "FAIL"


def test_feature_missing_impact_analysis_fails():
    delivery = _base_delivery()
    delivery.pop("impact_analysis")
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    impact_checks = [c for c in result.checks if c.check == "operational.impact_analysis"]
    assert impact_checks
    assert impact_checks[0].status == "FAIL"


def test_feature_with_operational_fields_passes():
    delivery = _base_delivery()
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    assum_checks = [c for c in result.checks if c.check == "operational.assumptions"]
    impact_checks = [c for c in result.checks if c.check == "operational.impact_analysis"]
    assert assum_checks[0].status == "PASS"
    assert impact_checks[0].status == "PASS"


def test_chore_exempt_from_operational_contract():
    """Chore tasks should not be gated on assumptions/impact — too much ceremony."""
    delivery = _base_delivery()
    delivery.pop("assumptions")
    delivery.pop("impact_analysis")
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "chore")
    # No FAIL on the operational rows for chore
    for c in result.checks:
        if c.check in ("operational.assumptions", "operational.impact_analysis"):
            assert c.status != "FAIL", f"chore unexpectedly FAILed on {c.check}"


# ---------- Regression: defensive coercion for malformed files_changed ----------

def test_files_changed_as_int_does_not_crash():
    """LLM sometimes emits files_changed as an int (count) rather than list[str].

    Regression guard: contract_validator must not raise TypeError on this shape.
    Behavior: malformed value coerced to empty set; consistency check still runs
    against changes (finds everything in changes as "not in impact" → warning).
    """
    delivery = _base_delivery()
    delivery["impact_analysis"] = {"files_changed": 1, "risk": "low"}
    # Must not raise
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    # Validation still completes — overall result set is non-empty
    assert result.checks


def test_files_changed_as_none_does_not_crash():
    delivery = _base_delivery()
    delivery["impact_analysis"] = {"files_changed": None, "risk": "low"}
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    assert result.checks


def test_files_changed_as_string_does_not_crash():
    """Degenerate case — LLM emits a path as a bare string, not [path]."""
    delivery = _base_delivery()
    delivery["impact_analysis"] = {"files_changed": "app/x.py", "risk": "low"}
    result = validate_delivery(delivery, _MINIMAL_CONTRACT, "feature")
    assert result.checks
