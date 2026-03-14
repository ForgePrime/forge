"""Tests for core.pipeline — task graph state machine (highest priority).

Tests cover:
- validate_dag (cycle detection, missing deps)
- State transitions (valid and invalid)
- add-tasks contract validation
- next task selection (deps, conflicts, decision blocking)
- complete with force
- Draft plan lifecycle (draft → approve)
- Subtask registration
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from pipeline import (
    validate_dag,
    save_tracker,
    load_tracker,
    find_task,
    CONTRACTS,
    cmd_add_tasks,
    cmd_next,
    cmd_complete,
    cmd_fail,
    cmd_skip,
    cmd_draft_plan,
    cmd_show_draft,
    cmd_approve_plan,
    cmd_register_subtasks,
    cmd_complete_subtask,
    _has_conflict,
    _blocked_by_open_decisions,
)
from contracts import validate_contract, atomic_write_json
from conftest import make_task


# ---------------------------------------------------------------------------
# validate_dag
# ---------------------------------------------------------------------------

class TestValidateDag:
    """Tests for DAG validation (cycle + missing dep detection)."""

    def test_valid_dag_passes(self):
        tasks = [
            {"id": "T-001", "depends_on": [], "conflicts_with": []},
            {"id": "T-002", "depends_on": ["T-001"], "conflicts_with": []},
            {"id": "T-003", "depends_on": ["T-001", "T-002"], "conflicts_with": []},
        ]
        errors = validate_dag(tasks)
        assert errors == []

    def test_circular_dependency_detected(self):
        tasks = [
            {"id": "T-001", "depends_on": ["T-002"], "conflicts_with": []},
            {"id": "T-002", "depends_on": ["T-001"], "conflicts_with": []},
        ]
        errors = validate_dag(tasks)
        assert any("ircular" in e for e in errors)

    def test_self_cycle_detected(self):
        tasks = [
            {"id": "T-001", "depends_on": ["T-001"], "conflicts_with": []},
        ]
        errors = validate_dag(tasks)
        assert any("ircular" in e for e in errors)

    def test_missing_dependency_detected(self):
        tasks = [
            {"id": "T-001", "depends_on": ["T-999"], "conflicts_with": []},
        ]
        errors = validate_dag(tasks)
        assert any("unknown" in e.lower() or "T-999" in e for e in errors)

    def test_missing_conflicts_with_reference(self):
        tasks = [
            {"id": "T-001", "depends_on": [], "conflicts_with": ["T-999"]},
        ]
        errors = validate_dag(tasks)
        assert any("T-999" in e for e in errors)

    def test_no_tasks_passes(self):
        errors = validate_dag([])
        assert errors == []

    def test_single_task_no_deps(self):
        tasks = [{"id": "T-001", "depends_on": [], "conflicts_with": []}]
        errors = validate_dag(tasks)
        assert errors == []

    def test_three_node_cycle_detected(self):
        tasks = [
            {"id": "T-001", "depends_on": ["T-003"], "conflicts_with": []},
            {"id": "T-002", "depends_on": ["T-001"], "conflicts_with": []},
            {"id": "T-003", "depends_on": ["T-002"], "conflicts_with": []},
        ]
        errors = validate_dag(tasks)
        assert any("ircular" in e for e in errors)


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

class TestStateTransitions:
    """Tests for task status lifecycle: TODO -> IN_PROGRESS -> DONE/FAILED/SKIPPED."""

    def test_todo_to_in_progress_via_next(self, forge_env, project_name):
        """next command moves TODO -> IN_PROGRESS."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [make_task("T-001", "first-task")],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, agent=None)
        cmd_next(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "IN_PROGRESS"
        assert reloaded["tasks"][0]["started_at"] is not None

    def test_in_progress_to_done_via_complete(self, forge_env, project_name):
        """complete moves IN_PROGRESS -> DONE."""
        task = make_task("T-001", "first-task", status="IN_PROGRESS")
        task["started_at"] = "2025-01-01T00:00:00Z"
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        # Create a change record so complete doesn't reject
        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            changes_dir / "changes.json",
            {"project": project_name, "updated": "", "changes": [
                {"id": "C-001", "task_id": "T-001", "file": "test.py",
                 "action": "create", "summary": "test"}
            ]},
        )

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="done")
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "DONE"
        assert reloaded["tasks"][0]["completed_at"] is not None

    def test_in_progress_to_failed(self, forge_env, project_name):
        """fail moves IN_PROGRESS -> FAILED with reason."""
        task = make_task("T-001", "first-task", status="IN_PROGRESS")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason="compilation error", agent=None)
        cmd_fail(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "FAILED"
        assert "compilation error" in reloaded["tasks"][0]["failed_reason"]

    def test_todo_to_skipped(self, forge_env, project_name):
        """skip moves TODO -> SKIPPED."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [make_task("T-001", "skip-me")],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001")
        cmd_skip(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "SKIPPED"

    def test_complete_with_force_bypasses_changes_check(self, forge_env, project_name):
        """--force allows completing without recorded changes."""
        task = make_task("T-001", "investigation", status="IN_PROGRESS")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=True, reasoning="no changes needed")
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "DONE"

    def test_complete_without_changes_exits(self, forge_env, project_name):
        """Complete without --force and no changes recorded should exit."""
        task = make_task("T-001", "needs-changes", status="IN_PROGRESS")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="",
                               ac_reasoning=None)
        with pytest.raises(SystemExit):
            cmd_complete(args)

    def test_complete_with_ac_requires_reasoning(self, forge_env, project_name):
        """Task with AC but no --ac-reasoning (and no --force) should exit."""
        task = make_task("T-001", "ac-task", status="IN_PROGRESS",
                         acceptance_criteria=["Feature X works", "Tests pass"])
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            changes_dir / "changes.json",
            {"project": project_name, "updated": "", "changes": [
                {"id": "C-001", "task_id": "T-001", "file": "test.py",
                 "action": "create", "summary": "test"}
            ]},
        )

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="done",
                               ac_reasoning=None)
        with pytest.raises(SystemExit):
            cmd_complete(args)

    def test_complete_with_ac_and_reasoning_succeeds(self, forge_env, project_name):
        """Task with AC + --ac-reasoning should complete successfully."""
        task = make_task("T-001", "ac-task", status="IN_PROGRESS",
                         acceptance_criteria=["Feature X works", "Tests pass"])
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            changes_dir / "changes.json",
            {"project": project_name, "updated": "", "changes": [
                {"id": "C-001", "task_id": "T-001", "file": "test.py",
                 "action": "create", "summary": "test"}
            ]},
        )

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="done",
                               ac_reasoning="1. Feature X works: verified. 2. Tests pass: pytest green.")
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "DONE"

    def test_complete_without_ac_skips_check(self, forge_env, project_name):
        """Task without AC should complete without --ac-reasoning."""
        task = make_task("T-001", "no-ac-task", status="IN_PROGRESS")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            changes_dir / "changes.json",
            {"project": project_name, "updated": "", "changes": [
                {"id": "C-001", "task_id": "T-001", "file": "test.py",
                 "action": "create", "summary": "test"}
            ]},
        )

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="done",
                               ac_reasoning=None)
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "DONE"

    def test_complete_with_ac_force_bypasses(self, forge_env, project_name):
        """--force bypasses AC reasoning requirement."""
        task = make_task("T-001", "ac-force-task", status="IN_PROGRESS",
                         acceptance_criteria=["Feature X works"])
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=True, reasoning="investigation only",
                               ac_reasoning=None)
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "DONE"

    def test_ac_reasoning_stored_on_task(self, forge_env, project_name):
        """After complete with AC reasoning, task should have ac_reasoning field."""
        task = make_task("T-001", "ac-stored-task", status="IN_PROGRESS",
                         acceptance_criteria=["Criterion A met"])
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            changes_dir / "changes.json",
            {"project": project_name, "updated": "", "changes": [
                {"id": "C-001", "task_id": "T-001", "file": "test.py",
                 "action": "create", "summary": "test"}
            ]},
        )

        ac_text = "Criterion A met: verified in integration test"
        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="done",
                               ac_reasoning=ac_text)
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["ac_reasoning"] == ac_text


# ---------------------------------------------------------------------------
# add-tasks contract validation
# ---------------------------------------------------------------------------

class TestAddTasksContract:
    """Tests for add-tasks contract validation."""

    def test_valid_task_passes(self):
        data = [{"id": "T-001", "name": "setup-db", "type": "feature"}]
        errors = validate_contract(CONTRACTS["add-tasks"], data)
        assert errors == []

    def test_missing_required_fields_rejected(self):
        data = [{"description": "no id or name"}]
        errors = validate_contract(CONTRACTS["add-tasks"], data)
        assert any("id" in e for e in errors)
        assert any("name" in e for e in errors)

    def test_invalid_type_rejected(self):
        data = [{"id": "T-001", "name": "x", "type": "INVALID_TYPE"}]
        errors = validate_contract(CONTRACTS["add-tasks"], data)
        assert any("type" in e.lower() for e in errors)

    def test_valid_types_accepted(self):
        for task_type in ["feature", "bug", "chore", "investigation"]:
            data = [{"id": "T-001", "name": "x", "type": task_type}]
            errors = validate_contract(CONTRACTS["add-tasks"], data)
            assert errors == [], f"type={task_type} should be valid"

    def test_depends_on_must_be_list(self):
        data = [{"id": "T-001", "name": "x", "depends_on": "T-002"}]
        errors = validate_contract(CONTRACTS["add-tasks"], data)
        assert any("list" in e for e in errors)

    def test_add_tasks_cmd_rejects_duplicate_ids(self, forge_env, project_name):
        """add-tasks rejects tasks whose ID already exists."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [make_task("T-001", "existing")],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(
            project=project_name,
            data=json.dumps([{"id": "T-001", "name": "duplicate"}]),
        )
        with pytest.raises(SystemExit):
            cmd_add_tasks(args)

    def test_add_tasks_cmd_succeeds(self, forge_env, project_name):
        """add-tasks adds valid tasks to tracker."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [],
        }
        save_tracker(project_name, tracker)

        tasks_data = [
            {"id": "T-001", "name": "first"},
            {"id": "T-002", "name": "second", "depends_on": ["T-001"]},
        ]
        args = SimpleNamespace(project=project_name, data=json.dumps(tasks_data))
        cmd_add_tasks(args)

        reloaded = load_tracker(project_name)
        assert len(reloaded["tasks"]) == 2
        assert reloaded["tasks"][1]["depends_on"] == ["T-001"]

    def test_add_tasks_rejects_circular_deps(self, forge_env, project_name):
        """add-tasks rejects task data with circular dependencies."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [],
        }
        save_tracker(project_name, tracker)

        tasks_data = [
            {"id": "T-001", "name": "a", "depends_on": ["T-002"]},
            {"id": "T-002", "name": "b", "depends_on": ["T-001"]},
        ]
        args = SimpleNamespace(project=project_name, data=json.dumps(tasks_data))
        with pytest.raises(SystemExit):
            cmd_add_tasks(args)


# ---------------------------------------------------------------------------
# next task selection logic
# ---------------------------------------------------------------------------

class TestNextTaskSelection:
    """Tests for next: deps check, conflicts, decision blocking."""

    def test_next_returns_task_with_deps_met(self, forge_env, project_name):
        """If T-001 is DONE, T-002 (depends on T-001) should be next."""
        t1 = make_task("T-001", "first", status="DONE")
        t1["completed_at"] = "2025-01-01T00:01:00Z"
        t2 = make_task("T-002", "second", depends_on=["T-001"])
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [t1, t2],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, agent=None)
        cmd_next(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][1]["status"] == "IN_PROGRESS"

    def test_next_skips_tasks_with_unmet_deps(self, forge_env, project_name):
        """T-002 depends on T-001 (TODO), so next should return T-003 (no deps)."""
        t1 = make_task("T-001", "blocker")
        t2 = make_task("T-002", "blocked", depends_on=["T-001"])
        t3 = make_task("T-003", "independent")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [t1, t2, t3],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, agent=None)
        cmd_next(args)

        reloaded = load_tracker(project_name)
        # T-001 is first TODO with no deps, so it should be picked
        assert reloaded["tasks"][0]["status"] == "IN_PROGRESS"

    def test_next_skips_tasks_blocked_by_open_decisions(self, forge_env, project_name):
        """Tasks blocked by OPEN decisions should be skipped by next."""
        t1 = make_task("T-001", "blocked-task", blocked_by_decisions=["D-001"])
        t2 = make_task("T-002", "free-task")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [t1, t2],
        }
        save_tracker(project_name, tracker)

        # Create decisions.json with D-001 OPEN
        dec_dir = Path("forge_output") / project_name
        dec_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            dec_dir / "decisions.json",
            {"project": project_name, "updated": "", "open_count": 1,
             "decisions": [{"id": "D-001", "status": "OPEN", "type": "architecture",
                            "task_id": "T-001", "issue": "test"}]},
        )

        args = SimpleNamespace(project=project_name, agent=None)
        cmd_next(args)

        reloaded = load_tracker(project_name)
        # T-001 blocked, T-002 should be picked
        assert reloaded["tasks"][0]["status"] == "TODO"  # T-001 still TODO
        assert reloaded["tasks"][1]["status"] == "IN_PROGRESS"  # T-002 picked

    def test_next_returns_existing_in_progress_task(self, forge_env, project_name):
        """If a task is already IN_PROGRESS, next returns it (resume)."""
        task = make_task("T-001", "in-flight", status="IN_PROGRESS")
        task["started_at"] = "2025-01-01T00:00:00Z"
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, agent=None)
        cmd_next(args)

        # Task should still be IN_PROGRESS (not changed)
        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "IN_PROGRESS"


# ---------------------------------------------------------------------------
# Conflict detection helper
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Tests for _has_conflict and _blocked_by_open_decisions helpers."""

    def test_no_conflict_when_no_conflicts_with(self):
        task = {"conflicts_with": []}
        assert _has_conflict(task, {"T-002"}) is False

    def test_conflict_detected(self):
        task = {"conflicts_with": ["T-002"]}
        assert _has_conflict(task, {"T-002"}) is True

    def test_no_conflict_when_conflicting_task_not_active(self):
        task = {"conflicts_with": ["T-002"]}
        assert _has_conflict(task, {"T-003"}) is False

    def test_blocked_by_open_decisions_returns_blocking_ids(self):
        task = {"blocked_by_decisions": ["D-001", "D-002"]}
        open_ids = {"D-001", "D-003"}
        result = _blocked_by_open_decisions(task, open_ids)
        assert result == ["D-001"]

    def test_not_blocked_when_decisions_closed(self):
        task = {"blocked_by_decisions": ["D-001"]}
        open_ids = set()  # all closed
        result = _blocked_by_open_decisions(task, open_ids)
        assert result == []


# ---------------------------------------------------------------------------
# Draft plan lifecycle
# ---------------------------------------------------------------------------

class TestDraftPlan:
    """Tests for draft-plan -> show-draft -> approve-plan workflow."""

    def test_draft_plan_stores_draft(self, forge_env, project_name):
        """draft-plan stores tasks as a draft, not in the pipeline."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [],
        }
        save_tracker(project_name, tracker)

        draft_data = [
            {"id": "T-001", "name": "first"},
            {"id": "T-002", "name": "second", "depends_on": ["T-001"]},
        ]
        args = SimpleNamespace(project=project_name,
                               data=json.dumps(draft_data),
                               idea=None)
        cmd_draft_plan(args)

        reloaded = load_tracker(project_name)
        assert len(reloaded["tasks"]) == 0  # NOT materialized yet
        assert "draft_plan" in reloaded
        assert len(reloaded["draft_plan"]["tasks"]) == 2

    def test_approve_plan_materializes_tasks(self, forge_env, project_name):
        """approve-plan moves draft tasks into the pipeline."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [],
            "draft_plan": {
                "source_idea_id": None,
                "created": "2025-01-01T00:00:00Z",
                "tasks": [
                    {"id": "T-001", "name": "first"},
                    {"id": "T-002", "name": "second", "depends_on": ["T-001"]},
                ],
            },
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name)
        cmd_approve_plan(args)

        reloaded = load_tracker(project_name)
        assert len(reloaded["tasks"]) == 2
        assert reloaded["tasks"][0]["status"] == "TODO"
        assert "draft_plan" not in reloaded

    def test_approve_plan_rejects_without_draft(self, forge_env, project_name):
        """approve-plan errors if no draft exists."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name)
        with pytest.raises(SystemExit):
            cmd_approve_plan(args)

    def test_approve_plan_rejects_duplicate_ids(self, forge_env, project_name):
        """approve-plan rejects if draft task IDs conflict with existing."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [make_task("T-001", "existing")],
            "draft_plan": {
                "source_idea_id": None,
                "created": "2025-01-01T00:00:00Z",
                "tasks": [{"id": "T-001", "name": "duplicate"}],
            },
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name)
        with pytest.raises(SystemExit):
            cmd_approve_plan(args)

    def test_draft_plan_with_idea_source(self, forge_env, project_name):
        """draft-plan stores source_idea_id when --idea is provided."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [],
        }
        save_tracker(project_name, tracker)

        draft_data = [{"id": "T-001", "name": "from-idea"}]
        args = SimpleNamespace(project=project_name,
                               data=json.dumps(draft_data),
                               idea="I-001")
        cmd_draft_plan(args)

        reloaded = load_tracker(project_name)
        assert reloaded["draft_plan"]["source_idea_id"] == "I-001"


# ---------------------------------------------------------------------------
# Subtask registration
# ---------------------------------------------------------------------------

class TestSubtasks:
    """Tests for subtask registration and completion."""

    def test_register_subtasks_on_in_progress_task(self, forge_env, project_name):
        """Subtasks can be registered on an IN_PROGRESS task."""
        task = make_task("T-001", "parent-task", status="IN_PROGRESS")
        task["started_at"] = "2025-01-01T00:00:00Z"
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        subtask_data = [
            {"id": "S-001", "name": "sub-one"},
            {"id": "S-002", "name": "sub-two"},
        ]
        args = SimpleNamespace(project=project_name, task_id="T-001",
                               data=json.dumps(subtask_data))
        cmd_register_subtasks(args)

        reloaded = load_tracker(project_name)
        parent = reloaded["tasks"][0]
        assert parent["has_subtasks"] is True
        assert parent["subtask_total"] == 2
        assert len(parent["subtasks"]) == 2
        assert parent["subtasks"][0]["id"] == "T-001/S-001"
        assert parent["subtasks"][1]["status"] == "TODO"

    def test_register_subtasks_rejects_non_in_progress(self, forge_env, project_name):
        """Cannot register subtasks on a TODO task."""
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [make_task("T-001", "todo-task")],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               data=json.dumps([{"id": "S-001", "name": "x"}]))
        with pytest.raises(SystemExit):
            cmd_register_subtasks(args)

    def test_complete_subtask(self, forge_env, project_name):
        """Completing a subtask updates parent counters."""
        task = make_task("T-001", "parent", status="IN_PROGRESS")
        task["started_at"] = "2025-01-01T00:00:00Z"
        task["has_subtasks"] = True
        task["subtask_total"] = 2
        task["subtask_done"] = 0
        task["subtasks"] = [
            {"id": "T-001/S-001", "name": "s1", "description": "",
             "status": "IN_PROGRESS", "started_at": "2025-01-01T00:00:00Z",
             "completed_at": None},
            {"id": "T-001/S-002", "name": "s2", "description": "",
             "status": "TODO", "started_at": None, "completed_at": None},
        ]
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, subtask_id="T-001/S-001")
        cmd_complete_subtask(args)

        reloaded = load_tracker(project_name)
        parent = reloaded["tasks"][0]
        assert parent["subtask_done"] == 1
        s1 = parent["subtasks"][0]
        assert s1["status"] == "DONE"
        assert s1["completed_at"] is not None
