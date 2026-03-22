"""Tests for core.models — round-trip, falsy preservation, extras overflow."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from models import (
    Task, Decision, Change, Guideline, Lesson, Knowledge, KnowledgeVersion,
    Idea, Objective, KeyResult, Research, AcTemplate,
)


# ---------------------------------------------------------------------------
# Round-trip identity: from_dict(d).to_dict() preserves all keys
# ---------------------------------------------------------------------------

class TestTaskRoundTrip:
    def test_basic_fields(self):
        d = {
            "id": "T-001", "name": "setup-db", "status": "TODO",
            "type": "feature", "depends_on": ["T-000"],
            "description": "Create schema", "instruction": "Run migrations",
        }
        _assert_superset_round_trip(Task, d)

    def test_runtime_fields(self):
        d = {
            "id": "T-002", "name": "test", "status": "DONE",
            "type": "feature", "depends_on": [],
            "branch": "forge/T-002", "worktree_path": "/tmp/wt",
            "started_at_commit": "abc123", "claimed_at": "2025-01-01T00:00:00Z",
            "gate_results": {"test": "pass"}, "ceremony_level": "STANDARD",
            "completion_trace": {"event": "complete"},
            "ac_verification_results": [{"text": "ok", "passed": True}],
            "ac_reasoning": "All criteria verified via tests",
            "deferred_decisions": [{"requirement": "x", "reason": "y"}],
            "skip_reason": None,  # None should be dropped
        }
        result = Task.from_dict(d).to_dict()
        assert result["branch"] == "forge/T-002"
        assert result["gate_results"] == {"test": "pass"}
        assert result["ac_verification_results"][0]["passed"] is True
        assert "skip_reason" not in result  # None dropped

    def test_unknown_future_fields_preserved(self):
        d = {
            "id": "T-003", "name": "test", "status": "TODO",
            "type": "chore", "depends_on": [],
            "some_future_field": "value",
            "another_unknown": [1, 2, 3],
        }
        result = Task.from_dict(d).to_dict()
        assert result["some_future_field"] == "value"
        assert result["another_unknown"] == [1, 2, 3]

    def test_empty_defaults_not_lost(self):
        """Empty strings and lists should survive round-trip."""
        d = {
            "id": "T-004", "name": "test", "status": "TODO",
            "type": "feature", "depends_on": [],
            "description": "", "instruction": "",
            "scopes": [], "exclusions": [],
        }
        result = Task.from_dict(d).to_dict()
        assert result["description"] == ""
        assert result["scopes"] == []

    def test_subtask_fields(self):
        d = {
            "id": "T-005", "name": "batch", "status": "IN_PROGRESS",
            "type": "feature", "depends_on": [],
            "has_subtasks": True, "subtask_total": 5, "subtask_done": 2,
            "subtasks": [{"id": "S-001", "status": "DONE"}],
        }
        result = Task.from_dict(d).to_dict()
        assert result["has_subtasks"] is True
        assert result["subtask_total"] == 5
        assert result["subtask_done"] == 2


class TestFalsyPreservation:
    """Falsy-but-meaningful values (0, False, "", []) must survive round-trip."""

    def test_zero_preserved(self):
        c = Change(id="C-001", lines_added=0, lines_removed=0)
        result = c.to_dict()
        assert result["lines_added"] == 0
        assert result["lines_removed"] == 0

        t = Task(id="T-001", name="t", subtask_total=0, subtask_done=0)
        result = t.to_dict()
        assert result["subtask_total"] == 0
        assert result["subtask_done"] == 0

    def test_false_preserved(self):
        t = Task(id="T-001", name="t", parallel=False, has_subtasks=False)
        result = t.to_dict()
        assert result["parallel"] is False
        assert result["has_subtasks"] is False

    def test_empty_string_preserved(self):
        t = Task(id="T-001", name="t", description="", origin="")
        result = t.to_dict()
        assert result["description"] == ""
        assert result["origin"] == ""

    def test_empty_list_preserved(self):
        t = Task(id="T-001", name="t", depends_on=[], scopes=[])
        result = t.to_dict()
        assert result["depends_on"] == []
        assert result["scopes"] == []


class TestNoneOmission:
    """None-valued optional fields should NOT appear in to_dict output."""

    def test_task_none_fields(self):
        t = Task(id="T-001", name="t")
        result = t.to_dict()
        assert "skill" not in result
        assert "alignment" not in result
        assert "produces" not in result
        assert "started_at" not in result
        assert "branch" not in result
        assert "gate_results" not in result

    def test_decision_none_fields(self):
        d = Decision(id="D-001", type="architecture")
        result = d.to_dict()
        assert "action" not in result
        assert "override_value" not in result
        assert "updated" not in result


# ---------------------------------------------------------------------------
# All model round-trips
# ---------------------------------------------------------------------------

def _assert_superset_round_trip(cls, d):
    """Assert all non-None original keys survive round-trip. Extra default-valued keys are OK."""
    result = cls.from_dict(d).to_dict()
    for key, value in d.items():
        if value is None:
            assert key not in result, f"None-valued key '{key}' should be dropped"
        else:
            assert key in result, f"Key '{key}' lost in round-trip"
            assert result[key] == value, f"Key '{key}' changed: {value!r} -> {result[key]!r}"


class TestAllModelsRoundTrip:
    def test_decision(self):
        _assert_superset_round_trip(Decision, {
            "id": "D-001", "task_id": "T-001", "type": "risk",
            "issue": "DB might be slow", "recommendation": "Add index",
            "severity": "HIGH", "likelihood": "MEDIUM",
            "status": "OPEN", "tags": ["perf"],
        })

    def test_change(self):
        _assert_superset_round_trip(Change, {
            "id": "C-001", "task_id": "T-001", "file": "schema.sql",
            "action": "create", "summary": "Added schema",
            "lines_added": 50, "lines_removed": 0,
            "timestamp": "2025-01-01T00:00:00Z",
        })

    def test_guideline(self):
        _assert_superset_round_trip(Guideline, {
            "id": "G-001", "title": "Use UTC", "scope": "backend",
            "content": "Always use UTC timestamps", "weight": "must",
            "status": "ACTIVE", "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
        })

    def test_lesson(self):
        _assert_superset_round_trip(Lesson, {
            "id": "L-001", "category": "mistake-avoided",
            "title": "Validate JWT aud", "detail": "We got burned",
            "severity": "critical", "tags": ["jwt"],
            "timestamp": "2025-01-01T00:00:00Z",
        })

    def test_knowledge(self):
        _assert_superset_round_trip(Knowledge, {
            "id": "K-001", "title": "Redis Stack", "category": "technical-context",
            "content": "Redis 7.4 supports...", "status": "ACTIVE", "version": 2,
            "versions": [{"version": 1, "content": "old"}],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        })

    def test_idea(self):
        _assert_superset_round_trip(Idea, {
            "id": "I-001", "title": "Add caching", "description": "Redis cache",
            "category": "feature", "priority": "HIGH", "status": "DRAFT",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
        })

    def test_objective(self):
        _assert_superset_round_trip(Objective, {
            "id": "O-001", "title": "Reduce latency", "description": "API p95 < 200ms",
            "key_results": [{"id": "KR-1", "metric": "p95", "target": 200}],
            "status": "ACTIVE",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
        })

    def test_research(self):
        _assert_superset_round_trip(Research, {
            "id": "R-001", "title": "Cache analysis", "topic": "Redis vs Memcached",
            "status": "DRAFT", "category": "architecture",
            "summary": "Redis recommended",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        })

    def test_ac_template(self):
        _assert_superset_round_trip(AcTemplate, {
            "id": "AC-001", "title": "Response Time",
            "template": "{endpoint} < {ms}ms", "category": "performance",
            "status": "ACTIVE", "usage_count": 3, "occurrences": 1,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        })

    def test_key_result(self):
        _assert_superset_round_trip(KeyResult, {
            "id": "KR-1", "metric": "p95 latency", "baseline": 500,
            "target": 200, "current": 350,
        })

    def test_knowledge_version(self):
        _assert_superset_round_trip(KnowledgeVersion, {
            "version": 2, "content": "updated", "changed_by": "user",
            "change_reason": "fix",
        })


# ---------------------------------------------------------------------------
# Extras overflow for ALL models
# ---------------------------------------------------------------------------

class TestExtrasOverflow:
    """Every model should preserve unknown keys via _extras."""

    @pytest.mark.parametrize("cls,base", [
        (Task, {"id": "T-1", "name": "t", "status": "TODO", "type": "feature", "depends_on": []}),
        (Decision, {"id": "D-1", "type": "architecture"}),
        (Change, {"id": "C-1"}),
        (Guideline, {"id": "G-1"}),
        (Lesson, {"id": "L-1"}),
        (Knowledge, {"id": "K-1"}),
        (Idea, {"id": "I-1"}),
        (Objective, {"id": "O-1"}),
        (Research, {"id": "R-1"}),
        (AcTemplate, {"id": "AC-1"}),
        (KeyResult, {"id": "KR-1"}),
        (KnowledgeVersion, {"version": 1}),
    ])
    def test_unknown_keys_preserved(self, cls, base):
        d = {**base, "future_field": "preserved", "nested_unknown": {"a": 1}}
        result = cls.from_dict(d).to_dict()
        assert result["future_field"] == "preserved"
        assert result["nested_unknown"] == {"a": 1}


# ---------------------------------------------------------------------------
# Schema equivalence with conftest.make_task
# ---------------------------------------------------------------------------

class TestSchemaEquivalence:
    def test_make_task_round_trips(self):
        """Task.from_dict(make_task(...)).to_dict() preserves all original keys."""
        from conftest import make_task
        original = make_task("T-001", name="test-task", status="TODO")
        _assert_superset_round_trip(Task, original)
