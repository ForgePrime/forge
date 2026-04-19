"""P5.3 — plan_gate.validate_plan_requirement_refs.

Pilot pain point: 10 plan tasks generated, 0 with requirement_refs back to
SRC-001..SRC-004. Re-tracing which task implements which requirement was
manual archaeology. The gate now blocks such plans before they're persisted."""
import pytest

from app.services.plan_gate import (
    _is_well_formed,
    validate_plan_requirement_refs,
)


# -----------------------------------------------------------------------------
# _is_well_formed
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("ref", [
    "SRC-001",
    "SRC-001 §2.4",
    "SRC-001 punkt 3",
    "SRC-002 sec 4.2",
    "FEAT-099 chapter 1",
])
def test_is_well_formed_accepts_valid_tokens(ref):
    assert _is_well_formed(ref) is True


@pytest.mark.parametrize("ref", [
    "",
    "   ",
    "SRC",         # no number
    "SRC-",        # no number
    "src-001",     # lowercase prefix not allowed
    "001-SRC",     # number first
    "SRC 001",     # missing dash
    None,
    123,
    [],
])
def test_is_well_formed_rejects_invalid(ref):
    assert _is_well_formed(ref) is False


# -----------------------------------------------------------------------------
# validate_plan_requirement_refs
# -----------------------------------------------------------------------------

def test_no_violations_when_project_has_no_sources():
    """Standalone projects (no /ingest) skip the gate entirely."""
    tasks = [{"external_id": "T-001", "type": "feature", "name": "x"}]  # no refs
    assert validate_plan_requirement_refs(tasks, project_has_source_docs=False) == []


def test_no_violations_when_tasks_list_is_empty():
    assert validate_plan_requirement_refs([], project_has_source_docs=True) == []


def test_chore_and_investigation_tasks_skip_the_gate():
    """Setup/exploration work doesn't need source attribution."""
    tasks = [
        {"external_id": "T-001", "type": "chore", "name": "set up CI"},
        {"external_id": "T-002", "type": "investigation", "name": "spike"},
        {"external_id": "T-003", "type": "analysis", "name": "diagram"},
    ]
    assert validate_plan_requirement_refs(tasks, project_has_source_docs=True) == []


def test_feature_task_without_refs_violates():
    tasks = [{"external_id": "T-005", "type": "feature", "name": "stock list"}]
    out = validate_plan_requirement_refs(tasks, project_has_source_docs=True)
    assert len(out) == 1
    assert "T-005" in out[0]
    assert "feature" in out[0]
    assert "requirement_refs" in out[0]


def test_bug_task_with_empty_refs_violates():
    tasks = [{"external_id": "T-008", "type": "bug",
              "name": "fix race", "requirement_refs": []}]
    out = validate_plan_requirement_refs(tasks, project_has_source_docs=True)
    assert len(out) == 1
    assert "T-008" in out[0]


def test_develop_task_with_refs_passes():
    tasks = [{"external_id": "T-002", "type": "develop", "name": "x",
              "requirement_refs": ["SRC-001 §3.2"]}]
    assert validate_plan_requirement_refs(tasks, project_has_source_docs=True) == []


def test_malformed_refs_are_flagged():
    tasks = [{"external_id": "T-010", "type": "feature", "name": "x",
              "requirement_refs": ["SRC-001 §2", "garbage", "lowercase-1"]}]
    out = validate_plan_requirement_refs(tasks, project_has_source_docs=True)
    assert len(out) == 1
    assert "malformed" in out[0]
    assert "T-010" in out[0]


def test_mixed_plan_returns_one_violation_per_offender():
    tasks = [
        {"external_id": "T-001", "type": "feature", "name": "ok",
         "requirement_refs": ["SRC-001 §1"]},
        {"external_id": "T-002", "type": "feature", "name": "missing"},
        {"external_id": "T-003", "type": "chore", "name": "skip"},
        {"external_id": "T-004", "type": "bug", "name": "bad refs",
         "requirement_refs": ["nope"]},
    ]
    out = validate_plan_requirement_refs(tasks, project_has_source_docs=True)
    assert len(out) == 2
    assert any("T-002" in v for v in out)
    assert any("T-004" in v for v in out)


def test_non_dict_task_entries_are_ignored():
    """Defensive: malformed JSON shouldn't crash the gate."""
    tasks = [None, "garbage", 42,
             {"external_id": "T-001", "type": "feature", "requirement_refs": ["SRC-001"]}]
    assert validate_plan_requirement_refs(tasks, project_has_source_docs=True) == []


def test_refs_must_be_list_not_string():
    """Common LLM mistake — emits a string instead of [string]."""
    tasks = [{"external_id": "T-007", "type": "feature", "name": "x",
              "requirement_refs": "SRC-001 §2"}]
    out = validate_plan_requirement_refs(tasks, project_has_source_docs=True)
    assert len(out) == 1
    assert "T-007" in out[0]


def test_violation_messages_include_helpful_hint():
    tasks = [{"external_id": "T-001", "type": "feature"}]
    out = validate_plan_requirement_refs(tasks, project_has_source_docs=True)
    assert "SRC-" in out[0]  # the hint shows expected token shape
