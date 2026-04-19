"""P5.5 — validator's file/test reference rule honors per-AC verification mode.

Bug surfaced by 2026-04-19 live E2E (run #207): T-001 had AC-2 with
`verification='command'` (alembic downgrade/upgrade). Claude's evidence was
command output. The validator demanded a file path or test name, rejected
3 attempts in a row, task FAILED.

These tests prove the per-AC rule swap:
  - verification='test' → must reference file/test path (legacy strict rule)
  - verification='command' → must reference command name OR shell output marker
  - verification='manual' → no structural check (rely on min_length only)
  - When ac_verifications is omitted, behavior matches the legacy strict path
    so callers that haven't been updated still work.
"""
import pytest

from app.services.contract_validator import (
    COMMAND_PATTERN, FILE_PATTERN, validate_delivery,
)


# Minimal contract that hits the AC-evidence path
_CONTRACT = {
    "required": {
        "reasoning": {"min_length": 1},
        "ac_evidence": {"min_length": 10, "must_reference_file_or_test": True,
                        "fail_blocks": True},
    },
    "optional": {},
    "anti_patterns": {},
}


def _make_delivery(*, ac_evidence: list[dict], reasoning: str = "x" * 50,
                   include_op: bool = True) -> dict:
    """Build a delivery skeleton that satisfies non-AC rules so we isolate the AC checks."""
    d = {
        "reasoning": reasoning,
        "ac_evidence": ac_evidence,
        # Operational contract is required for feature/bug; satisfy it
        "assumptions": [],
        "impact_analysis": {"summary": "x"},
        "completion_claims": {},
        "changes": [],
    }
    return d


# ---- COMMAND_PATTERN heuristic --------------------------------------

@pytest.mark.parametrize("evidence", [
    "Ran `alembic downgrade -1` then `alembic upgrade head`. Output: OK.",
    "$ pytest tests/foo.py — 12 passed in 0.4s",
    "docker compose up -d, postgres healthy",
    "exit code: 0",
    "stdout: 1500 req/s",
    "rc=0 — apply succeeded",
    "kubectl rollout status: deployment ready",
    ">>> import x; x.run()",
])
def test_command_pattern_matches_typical_command_evidence(evidence):
    assert COMMAND_PATTERN.search(evidence), f"should match: {evidence!r}"


@pytest.mark.parametrize("evidence", [
    "verified manually",
    "looks correct",
    "everything works",
    "I checked it",
])
def test_command_pattern_does_not_match_self_report_phrases(evidence):
    assert COMMAND_PATTERN.search(evidence) is None, f"shouldn't match: {evidence!r}"


# ---- Per-AC verification — rule swap --------------------------------

def test_command_ac_with_command_evidence_passes():
    """Pre-fix: this combo would FAIL (no file/test ref). Post-fix: PASSES."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 2, "verdict": "PASS",
         "evidence": "Ran `alembic downgrade -1 && alembic upgrade head`. Output: OK.",
         "scenario_type": "regression"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={2: "command"})
    ref_check = next((c for c in result.checks if c.check == "ac_evidence[2].ref"), None)
    assert ref_check is not None
    assert ref_check.status == "PASS", f"detail: {ref_check.detail}"


def test_command_ac_with_self_report_fails_with_specific_hint():
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 2, "verdict": "PASS",
         "evidence": "Verified manually that the command works correctly.",
         "scenario_type": "regression"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={2: "command"})
    ref_check = next((c for c in result.checks if c.check == "ac_evidence[2].ref"), None)
    assert ref_check.status == "FAIL"
    assert "verification='command'" in result.fix_instructions
    assert any(s in result.fix_instructions.lower()
               for s in ["command name", "shell prompt", "exit-code"])


def test_test_ac_still_requires_file_or_test_ref():
    """Legacy strict behavior preserved for verification='test'."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS",
         "evidence": "test passed in suite",  # no file path, no test name
         "scenario_type": "positive"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "test"})
    ref_check = next((c for c in result.checks if c.check == "ac_evidence[0].ref"), None)
    assert ref_check.status == "FAIL"
    assert "verification='test'" in result.fix_instructions


def test_test_ac_with_test_node_id_passes():
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS",
         "evidence": "tests/stock/test_service.py::test_alpha PASSED",
         "scenario_type": "positive"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "test"})
    ref_check = next((c for c in result.checks if c.check == "ac_evidence[0].ref"), None)
    assert ref_check.status == "PASS"


def test_manual_ac_skips_reference_rule_entirely():
    """Manual ACs are user-judgment; structural enforcement is off."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 1, "verdict": "PASS",
         "evidence": "User accepted via UI walkthrough on 2026-04-19.",
         "scenario_type": "positive"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={1: "manual"})
    ref_check = next((c for c in result.checks if c.check == "ac_evidence[1].ref"), None)
    assert ref_check.status == "PASS"
    assert "skipped" in (ref_check.detail or "")


def test_default_to_test_when_no_map_given():
    """Backwards-compat: callers that pre-date P5.5 should still see strict behavior."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS",
         "evidence": "Ran alembic upgrade head — OK.",  # no file/test ref
         "scenario_type": "positive"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature")  # no ac_verifications
    ref_check = next((c for c in result.checks if c.check == "ac_evidence[0].ref"), None)
    # Without the map, falls back to strict 'test' rule → no file/test → FAIL
    assert ref_check.status == "FAIL"


def test_mixed_ac_types_in_one_delivery():
    """Common case: a real task has 1 'test' AC + 1 'command' AC + 1 'manual' AC."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS",
         "evidence": "tests/db/test_schema.py::test_tables_created PASSED",
         "scenario_type": "positive"},
        {"ac_index": 1, "verdict": "PASS",
         "evidence": "tests/db/test_schema.py::test_unique_constraint PASSED — DETAIL: duplicate insert raised IntegrityError",
         "scenario_type": "negative"},
        {"ac_index": 2, "verdict": "PASS",
         "evidence": "$ alembic downgrade -1 && alembic upgrade head — exit code 0",
         "scenario_type": "regression"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "test", 1: "test", 2: "command"})
    refs = [c for c in result.checks if c.check.startswith("ac_evidence[") and c.check.endswith(".ref")]
    assert len(refs) == 3
    assert all(r.status == "PASS" for r in refs), [r.check + ":" + r.status for r in refs]


def test_unknown_verification_falls_back_to_test_rule():
    """Defensive: if the map has a typo / unknown value, treat as strict."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS",
         "evidence": "Ran alembic — works.",  # no file ref
         "scenario_type": "positive"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "weirdo-mode"})
    ref_check = next((c for c in result.checks if c.check == "ac_evidence[0].ref"), None)
    # Unknown → falls into the else branch (strict 'test')
    assert ref_check.status == "FAIL"


def test_min_length_still_enforced_for_command_evidence():
    """A 'command' AC with very short evidence still fails the length check."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS", "evidence": "ok",  # 2 chars < 10
         "scenario_type": "positive"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "command"})
    len_check = next((c for c in result.checks if c.check == "ac_evidence[0].length"), None)
    assert len_check.status == "FAIL"


def test_validator_accepts_reasoning_with_word_done():
    """P5.9 — `done` was rejected as a substring everywhere. Now accepted in normal context."""
    delivery = _make_delivery(
        reasoning=(
            "The migration is done in app/migrations/0001.py because we needed to "
            "create products and warehouses tables before any FK could reference them. "
            "Schema verified by running pytest tests/db/test_schema.py."
        ),
        ac_evidence=[{
            "ac_index": 0, "verdict": "PASS",
            "evidence": "tests/db/test_schema.py::test_tables_created PASSED",
            "scenario_type": "positive",
        }],
    )
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "test"})
    rej = next((c for c in result.checks if c.check == "reasoning.reject_pattern"), None)
    assert rej is None, "P5.9: reasoning containing 'done' in normal context should NOT be rejected"


def test_validator_still_rejects_explicit_self_report():
    """The intent of REJECT_PATTERNS_REASONING — true self-report shortcuts — still works."""
    delivery = _make_delivery(
        reasoning="The migration looks good because I checked it. Everything works.",
        ac_evidence=[{
            "ac_index": 0, "verdict": "PASS",
            "evidence": "tests/db/test_schema.py::test_x PASSED",
            "scenario_type": "positive",
        }],
    )
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "test"})
    rej = next((c for c in result.checks if c.check == "reasoning.reject_pattern"), None)
    assert rej is not None
    assert rej.status == "FAIL"


def test_min_length_still_enforced_for_manual_evidence():
    """A 'manual' AC must still meet min_length (we only relaxed the ref rule)."""
    delivery = _make_delivery(ac_evidence=[
        {"ac_index": 0, "verdict": "PASS", "evidence": "ok",  # 2 chars
         "scenario_type": "positive"},
    ])
    result = validate_delivery(delivery, _CONTRACT, "feature",
                                ac_verifications={0: "manual"})
    len_check = next((c for c in result.checks if c.check == "ac_evidence[0].length"), None)
    assert len_check.status == "FAIL"
