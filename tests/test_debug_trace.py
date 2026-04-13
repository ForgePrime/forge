"""Tests for debug/trace system — FORGE_DEBUG, _trace(), completion_trace.

Tests cover:
- _is_debug reads FORGE_DEBUG env var correctly
- _is_debug reads .env file when env var not set
- _is_debug defaults to False when nothing set
- _trace writes JSONL when debug enabled
- _trace does NOT write when debug disabled
- completion_trace is saved on task after cmd_complete
- trace entries have correct structure (ts, event)
- trace captures AC verification details
- trace captures gate execution details
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from pipeline import (
    _is_debug,
    _trace,
    _debug_enabled,
    _DEBUG_CHECKED,
    cmd_complete,
    cmd_skip,
    cmd_fail,
    cmd_next,
    cmd_begin,
    cmd_draft_plan,
    cmd_approve_plan,
    _validate_ac_reasoning,
    _validate_plan_context,
    _verify_acceptance_criteria,
    _auto_update_kr,
    save_tracker,
    load_tracker,
    find_task,
)
from contracts import atomic_write_json
from conftest import make_task


def _reset_debug(monkeypatch, enabled=True):
    """Helper: set FORGE_DEBUG and reset cache."""
    import pipeline
    if enabled:
        monkeypatch.setenv("FORGE_DEBUG", "true")
    else:
        monkeypatch.delenv("FORGE_DEBUG", raising=False)
    pipeline._DEBUG_CHECKED = None


def _cleanup_debug():
    """Reset debug cache after test."""
    import pipeline
    pipeline._DEBUG_CHECKED = None


def _read_trace(path, project):
    """Read trace.jsonl and return list of parsed entries."""
    trace_file = path / "forge_output" / project / "trace.jsonl"
    if not trace_file.exists():
        return []
    return [json.loads(line) for line in
            trace_file.read_text(encoding="utf-8").strip().split("\n") if line.strip()]


def _trace_events(entries):
    """Extract event names from trace entries."""
    return [e.get("event") or e.get("cmd") for e in entries]


# ---------------------------------------------------------------------------
# _is_debug tests
# ---------------------------------------------------------------------------

class TestIsDebug:
    """Tests for _is_debug() env var and .env file reading."""

    def test_debug_false_by_default(self, monkeypatch):
        """No env var, no .env file → False."""
        monkeypatch.delenv("FORGE_DEBUG", raising=False)
        monkeypatch.chdir(Path(__file__).parent)  # no .env here
        assert _is_debug() is False

    def test_debug_true_from_env(self, monkeypatch):
        """FORGE_DEBUG=true in env → True."""
        monkeypatch.setenv("FORGE_DEBUG", "true")
        assert _is_debug() is True

    def test_debug_true_from_env_1(self, monkeypatch):
        """FORGE_DEBUG=1 in env → True."""
        monkeypatch.setenv("FORGE_DEBUG", "1")
        assert _is_debug() is True

    def test_debug_false_from_env(self, monkeypatch):
        """FORGE_DEBUG=false in env → False."""
        monkeypatch.setenv("FORGE_DEBUG", "false")
        assert _is_debug() is False

    def test_debug_true_from_dotenv(self, tmp_path, monkeypatch):
        """FORGE_DEBUG=true in .env file → True."""
        monkeypatch.delenv("FORGE_DEBUG", raising=False)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("FORGE_DEBUG=true\n", encoding="utf-8")
        assert _is_debug() is True

    def test_debug_from_dotenv_with_quotes(self, tmp_path, monkeypatch):
        """FORGE_DEBUG="true" (quoted) in .env → True."""
        monkeypatch.delenv("FORGE_DEBUG", raising=False)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text('FORGE_DEBUG="true"\n', encoding="utf-8")
        assert _is_debug() is True

    def test_debug_dotenv_with_comments(self, tmp_path, monkeypatch):
        """Comments and other vars in .env don't interfere."""
        monkeypatch.delenv("FORGE_DEBUG", raising=False)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "# comment\nOTHER_VAR=123\nFORGE_DEBUG=true\nMORE=abc\n",
            encoding="utf-8"
        )
        assert _is_debug() is True

    def test_debug_false_from_dotenv(self, tmp_path, monkeypatch):
        """FORGE_DEBUG=false in .env → False."""
        monkeypatch.delenv("FORGE_DEBUG", raising=False)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("FORGE_DEBUG=false\n", encoding="utf-8")
        assert _is_debug() is False

    def test_env_var_overrides_dotenv(self, tmp_path, monkeypatch):
        """Env var takes precedence over .env file."""
        monkeypatch.setenv("FORGE_DEBUG", "false")
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("FORGE_DEBUG=true\n", encoding="utf-8")
        assert _is_debug() is False


# ---------------------------------------------------------------------------
# _trace tests
# ---------------------------------------------------------------------------

class TestTrace:
    """Tests for _trace() JSONL writing."""

    def test_trace_writes_when_debug_enabled(self, tmp_path, monkeypatch):
        """_trace appends JSONL line when FORGE_DEBUG=true."""
        import pipeline
        monkeypatch.setenv("FORGE_DEBUG", "true")
        monkeypatch.chdir(tmp_path)
        pipeline._DEBUG_CHECKED = None  # Reset cache

        _trace("test-proj", {"event": "test.hello", "data": 42})

        trace_file = tmp_path / "forge_output" / "test-proj" / "trace.jsonl"
        assert trace_file.exists()
        lines = trace_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event"] == "test.hello"
        assert entry["data"] == 42
        assert "ts" in entry

        # Reset
        pipeline._DEBUG_CHECKED = None

    def test_trace_does_not_write_when_debug_disabled(self, tmp_path, monkeypatch):
        """_trace does nothing when FORGE_DEBUG is not set."""
        import pipeline
        monkeypatch.delenv("FORGE_DEBUG", raising=False)
        monkeypatch.chdir(tmp_path)
        pipeline._DEBUG_CHECKED = None  # Reset cache

        _trace("test-proj", {"event": "test.should_not_exist"})

        trace_file = tmp_path / "forge_output" / "test-proj" / "trace.jsonl"
        assert not trace_file.exists()

        # Reset
        pipeline._DEBUG_CHECKED = None

    def test_trace_appends_multiple_entries(self, tmp_path, monkeypatch):
        """Multiple _trace calls append separate JSONL lines."""
        import pipeline
        monkeypatch.setenv("FORGE_DEBUG", "true")
        monkeypatch.chdir(tmp_path)
        pipeline._DEBUG_CHECKED = None

        _trace("test-proj", {"event": "first"})
        _trace("test-proj", {"event": "second"})
        _trace("test-proj", {"event": "third"})

        trace_file = tmp_path / "forge_output" / "test-proj" / "trace.jsonl"
        lines = trace_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0])["event"] == "first"
        assert json.loads(lines[1])["event"] == "second"
        assert json.loads(lines[2])["event"] == "third"

        pipeline._DEBUG_CHECKED = None

    def test_trace_handles_complex_data(self, tmp_path, monkeypatch):
        """_trace serializes complex nested data structures."""
        import pipeline
        monkeypatch.setenv("FORGE_DEBUG", "true")
        monkeypatch.chdir(tmp_path)
        pipeline._DEBUG_CHECKED = None

        _trace("test-proj", {
            "event": "complex",
            "list": [1, 2, 3],
            "nested": {"a": {"b": "c"}},
            "unicode": "zażółć gęślą jaźń",
        })

        trace_file = tmp_path / "forge_output" / "test-proj" / "trace.jsonl"
        entry = json.loads(trace_file.read_text(encoding="utf-8").strip())
        assert entry["unicode"] == "zażółć gęślą jaźń"
        assert entry["nested"]["a"]["b"] == "c"

        pipeline._DEBUG_CHECKED = None


# ---------------------------------------------------------------------------
# completion_trace on task
# ---------------------------------------------------------------------------

class TestCompletionTrace:
    """Tests for completion_trace dict saved on task after cmd_complete."""

    def test_completion_trace_saved_on_task(self, forge_env, project_name):
        """cmd_complete saves completion_trace with ceremony, duration, AC counts."""
        task = make_task("T-001", "trace-test", status="IN_PROGRESS",
                         task_type="chore")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=True, reasoning="test",
                               ac_reasoning=None, deferred=None)
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        t = reloaded["tasks"][0]
        assert "completion_trace" in t
        ct = t["completion_trace"]
        assert ct["ceremony"] == "MINIMAL"
        assert isinstance(ct["duration_ms"], int)
        assert ct["duration_ms"] >= 0
        assert ct["ac_mechanical_count"] == 0
        assert ct["ac_manual_count"] == 0
        assert ct["gates_configured"] is False

    def test_completion_trace_counts_ac(self, forge_env, project_name):
        """completion_trace correctly counts manual and mechanical AC."""
        task = make_task("T-001", "ac-trace", status="IN_PROGRESS",
                         acceptance_criteria=[
                             "Manual criterion A",
                             "Manual criterion B",
                             {"text": "Check lint", "verification": "command",
                              "command": "echo ok"},
                         ])
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        # Need changes for STANDARD ceremony
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
                               ac_reasoning="AC 1: Manual criterion A — PASS: verified in code at app.py:42, returns expected value. AC 2: Manual criterion B — PASS: checked via manual inspection of output logs.",
                               deferred="[]")
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        ct = reloaded["tasks"][0]["completion_trace"]
        assert ct["ac_manual_count"] == 2
        assert ct["ac_mechanical_count"] == 1  # "echo ok" command
        assert ct["ac_mechanical_passed"] == 1
        assert ct["ac_mechanical_failed"] == 0
        assert ct["ac_reasoning_length"] > 50


# ---------------------------------------------------------------------------
# Trace integration with complete
# ---------------------------------------------------------------------------

class TestTraceIntegration:
    """Tests that cmd_complete writes trace entries when debug enabled."""

    def test_complete_writes_trace_entries(self, forge_env, project_name, monkeypatch):
        """cmd_complete writes multiple trace entries to trace.jsonl."""
        _reset_debug(monkeypatch, True)

        task = make_task("T-001", "traced-task", status="IN_PROGRESS",
                         task_type="chore")
        tracker = {
            "project": project_name,
            "goal": "Test",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "tasks": [task],
        }
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=True, reasoning="test",
                               ac_reasoning=None, deferred=None)
        cmd_complete(args)

        entries = _read_trace(forge_env, project_name)
        events = _trace_events(entries)

        assert "complete.start" in events
        assert "complete.ceremony" in events
        assert "complete.check_reasoning" in events
        assert "complete.ac_start" in events

        # Every entry should have timestamp
        for entry in entries:
            assert "ts" in entry

        _cleanup_debug()


# ---------------------------------------------------------------------------
# Edge cases: skip
# ---------------------------------------------------------------------------

class TestSkipEdgeCases:
    """Edge cases for cmd_skip with new --reason and --force requirements."""

    def test_skip_without_reason_fails(self, forge_env, project_name):
        """Skip without --reason must fail."""
        task = make_task("T-001", "skip-no-reason", status="IN_PROGRESS",
                         task_type="chore")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason="", force=False)
        with pytest.raises(SystemExit):
            cmd_skip(args)

    def test_skip_with_short_reason_fails(self, forge_env, project_name):
        """Skip with reason < 50 chars must fail."""
        task = make_task("T-001", "skip-short", status="IN_PROGRESS",
                         task_type="chore")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason="too short", force=False)
        with pytest.raises(SystemExit):
            cmd_skip(args)

    def test_skip_feature_without_force_fails(self, forge_env, project_name):
        """Feature task skip without --force must fail."""
        task = make_task("T-001", "skip-feature", status="IN_PROGRESS",
                         task_type="feature")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason="This task is blocked by external dependency from Warsaw team, cannot proceed until Q3.",
                               force=False)
        with pytest.raises(SystemExit):
            cmd_skip(args)

    def test_skip_feature_with_force_succeeds(self, forge_env, project_name):
        """Feature task skip WITH --force and valid reason succeeds."""
        task = make_task("T-001", "skip-feature-force", status="IN_PROGRESS",
                         task_type="feature")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason="This task is blocked by external dependency from Warsaw team, cannot proceed until Q3.",
                               force=True)
        cmd_skip(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "SKIPPED"
        assert "skip_reason" in reloaded["tasks"][0]
        assert len(reloaded["tasks"][0]["skip_reason"]) >= 50

    def test_skip_bug_without_force_fails(self, forge_env, project_name):
        """Bug task skip without --force must fail."""
        task = make_task("T-001", "skip-bug", status="IN_PROGRESS",
                         task_type="bug")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason="Cannot reproduce this bug in current environment, needs production data to verify.",
                               force=False)
        with pytest.raises(SystemExit):
            cmd_skip(args)

    def test_skip_chore_without_force_succeeds(self, forge_env, project_name):
        """Chore task skip with valid reason but no --force succeeds."""
        task = make_task("T-001", "skip-chore", status="IN_PROGRESS",
                         task_type="chore")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason="Documentation update deferred — waiting for architecture review to finalize before documenting.",
                               force=False)
        cmd_skip(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "SKIPPED"

    def test_skip_writes_trace(self, forge_env, project_name, monkeypatch):
        """Skip writes trace entry with reason and force flag."""
        _reset_debug(monkeypatch, True)

        task = make_task("T-001", "skip-traced", status="IN_PROGRESS",
                         task_type="chore")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        reason = "Task superseded by new requirements from stakeholder meeting on 2026-03-20."
        args = SimpleNamespace(project=project_name, task_id="T-001",
                               reason=reason, force=False)
        cmd_skip(args)

        entries = _read_trace(forge_env, project_name)
        skip_entries = [e for e in entries if e.get("cmd") == "skip"]
        assert len(skip_entries) == 1
        assert skip_entries[0]["reason"] == reason
        assert skip_entries[0]["task"] == "T-001"

        _cleanup_debug()


# ---------------------------------------------------------------------------
# Edge cases: AC verification
# ---------------------------------------------------------------------------

class TestACVerificationEdgeCases:
    """Edge cases for AC verification at completion."""

    def test_mechanical_ac_blocks_even_chore(self, forge_env, project_name):
        """Mechanical AC (command) blocks completion even for chore tasks."""
        task = make_task("T-001", "chore-with-ac", status="IN_PROGRESS",
                         task_type="chore",
                         acceptance_criteria=[
                             {"text": "Lint must pass", "verification": "command",
                              "command": "exit 1"},  # Will fail
                         ])
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="test",
                               ac_reasoning=None, deferred=None)
        with pytest.raises(SystemExit):
            cmd_complete(args)

    def test_mechanical_ac_passes_chore(self, forge_env, project_name):
        """Mechanical AC (command) that passes allows chore completion."""
        task = make_task("T-001", "chore-ac-pass", status="IN_PROGRESS",
                         task_type="chore",
                         acceptance_criteria=[
                             {"text": "Echo works", "verification": "command",
                              "command": "echo hello"},
                         ])
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=True, reasoning="test",
                               ac_reasoning=None, deferred=None)
        cmd_complete(args)

        reloaded = load_tracker(project_name)
        assert reloaded["tasks"][0]["status"] == "DONE"
        assert reloaded["tasks"][0]["ac_verification_results"][0]["passed"] is True

    def test_ac_reasoning_too_short_fails(self, forge_env, project_name):
        """AC reasoning < 50 chars must fail."""
        task = make_task("T-001", "short-reasoning", status="IN_PROGRESS",
                         acceptance_criteria=["Feature works"])
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(changes_dir / "changes.json",
                          {"project": project_name, "updated": "", "changes": [
                              {"id": "C-001", "task_id": "T-001", "file": "x.py",
                               "action": "create", "summary": "test"}]})

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="done",
                               ac_reasoning="done", deferred="[]")
        with pytest.raises(SystemExit):
            cmd_complete(args)

    def test_ac_reasoning_filler_only_fails(self, forge_env, project_name):
        """AC reasoning with only filler words must fail (no verdict keyword)."""
        task = make_task("T-001", "filler-reasoning", status="IN_PROGRESS",
                         acceptance_criteria=["Feature works"])
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(changes_dir / "changes.json",
                          {"project": project_name, "updated": "", "changes": [
                              {"id": "C-001", "task_id": "T-001", "file": "x.py",
                               "action": "create", "summary": "test"}]})

        # Addresses AC 1 but no PASS/met/verified verdict → validation fails
        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="done",
                               ac_reasoning="AC 1: Feature works — looks good, everything is fine and working correctly as expected.",
                               deferred="[]")
        with pytest.raises(SystemExit):
            cmd_complete(args)

    def test_ac_reasoning_not_addressing_all_criteria_fails(self, forge_env, project_name):
        """AC reasoning that misses a criterion must fail."""
        task = make_task("T-001", "missing-ac", status="IN_PROGRESS",
                         acceptance_criteria=["API returns 200", "Tests pass", "Logs written"])
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        changes_dir = Path("forge_output") / project_name
        changes_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(changes_dir / "changes.json",
                          {"project": project_name, "updated": "", "changes": [
                              {"id": "C-001", "task_id": "T-001", "file": "x.py",
                               "action": "create", "summary": "test"}]})

        # Only addresses AC 1 and 2, not AC 3
        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=False, reasoning="implemented",
                               ac_reasoning="AC 1: API returns 200 — PASS: tested with curl localhost:8000/api, got 200 OK. AC 2: Tests pass — PASS: pytest tests/ passed 15/15.",
                               deferred="[]")
        with pytest.raises(SystemExit):
            cmd_complete(args)

    def test_mechanical_ac_traces_command_output(self, forge_env, project_name, monkeypatch):
        """Trace captures command output from mechanical AC."""
        _reset_debug(monkeypatch, True)

        task = make_task("T-001", "traced-ac", status="IN_PROGRESS",
                         task_type="chore",
                         acceptance_criteria=[
                             {"text": "Echo test", "verification": "command",
                              "command": "echo trace_test_output"},
                         ])
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        args = SimpleNamespace(project=project_name, task_id="T-001",
                               agent=None, force=True, reasoning="test",
                               ac_reasoning=None, deferred=None)
        cmd_complete(args)

        entries = _read_trace(forge_env, project_name)
        cmd_results = [e for e in entries if e.get("event") == "ac.command_result"]
        assert len(cmd_results) == 1
        assert cmd_results[0]["passed"] is True
        assert "trace_test_output" in cmd_results[0]["output"]
        assert cmd_results[0]["command"] == "echo trace_test_output"
        assert "duration_ms" in cmd_results[0]

        _cleanup_debug()


# ---------------------------------------------------------------------------
# Edge cases: _validate_ac_reasoning
# ---------------------------------------------------------------------------

class TestValidateACReasoningEdgeCases:
    """Edge cases for AC reasoning validation logic."""

    def test_structured_ac_with_command_skipped_in_reasoning(self):
        """Mechanical AC (command) should not require reasoning — only manual AC does."""
        ac = [
            {"text": "Lint passes", "verification": "command", "command": "ruff check ."},
            "Manual check: UI renders correctly",
        ]
        # Only addresses AC 1 (the manual one, which is "1." in manual-only list)
        reasoning = "AC 1: Manual check: UI renders correctly — PASS: opened browser, page loads with correct layout at /dashboard"
        errors = _validate_ac_reasoning(reasoning, ac)
        assert errors == []

    def test_empty_ac_list_no_errors(self):
        """Empty AC list should produce no errors."""
        errors = _validate_ac_reasoning("anything goes here really", [])
        assert errors == []

    def test_text_fragment_matching_works(self):
        """Criterion recognized by text fragment even without numbered format."""
        ac = ["endpoint returns 200 for valid requests"]
        reasoning = "endpoint returns 200 for valid requests — PASS: verified with curl, got HTTP 200 and valid JSON body"
        errors = _validate_ac_reasoning(reasoning, ac)
        assert errors == []


# ---------------------------------------------------------------------------
# Edge cases: _validate_plan_context
# ---------------------------------------------------------------------------

class TestPlanContextValidation:
    """Edge cases for draft-plan context auto-validation."""

    def test_task_with_origin_but_no_scopes_produces_error(self, forge_env, project_name):
        """Task with origin O-XXX but no scopes when objective has scopes → error."""
        _s = __import__("pipeline")._get_storage()
        # Create objective with scopes
        obj_data = {"project": project_name, "updated": "", "objectives": [
            {"id": "O-001", "title": "Test", "status": "ACTIVE",
             "scopes": ["backend"], "key_results": []}
        ]}
        _s.save_data(project_name, 'objectives', obj_data)

        entries = [{"id": "T-001", "name": "test", "type": "feature",
                    "origin": "O-001", "scopes": [],
                    "acceptance_criteria": ["works"], "knowledge_ids": []}]

        errors, summary = _validate_plan_context(entries, project_name)
        assert any("scopes" in e.lower() for e in errors)

    def test_must_guidelines_scope_not_covered_produces_error(self, forge_env, project_name):
        """Must-guidelines with scope not covered by any task → error."""
        _s = __import__("pipeline")._get_storage()
        g_data = {"project": project_name, "updated": "", "guidelines": [
            {"id": "G-001", "title": "Security", "scope": "security",
             "weight": "must", "status": "ACTIVE", "content": "Use HTTPS"}
        ]}
        _s.save_data(project_name, 'guidelines', g_data)

        entries = [{"id": "T-001", "name": "test", "type": "feature",
                    "scopes": ["backend"],  # no "security" scope
                    "acceptance_criteria": ["works"], "knowledge_ids": []}]

        errors, summary = _validate_plan_context(entries, project_name)
        assert any("security" in e.lower() for e in errors)

    def test_no_guidelines_no_errors(self, forge_env, project_name):
        """No guidelines in project → no context errors."""
        entries = [{"id": "T-001", "name": "test", "type": "feature",
                    "scopes": ["backend"],
                    "acceptance_criteria": ["works"], "knowledge_ids": []}]

        errors, summary = _validate_plan_context(entries, project_name)
        assert errors == []

    def test_knowledge_exists_but_not_linked_shows_note(self, forge_env, project_name):
        """Knowledge objects exist but no task links them → note in summary."""
        _s = __import__("pipeline")._get_storage()
        k_data = {"project": project_name, "updated": "", "knowledge": [
            {"id": "K-001", "title": "API Design", "category": "architecture",
             "status": "ACTIVE", "content": "REST conventions", "scopes": ["backend"]}
        ]}
        _s.save_data(project_name, 'knowledge', k_data)

        entries = [{"id": "T-001", "name": "test", "type": "feature",
                    "scopes": ["backend"],
                    "acceptance_criteria": ["works"], "knowledge_ids": []}]

        errors, summary = _validate_plan_context(entries, project_name)
        assert any("K-001" in line for line in summary)


# ---------------------------------------------------------------------------
# Edge cases: KR auto-update
# ---------------------------------------------------------------------------

class TestKRAutoUpdateEdgeCases:
    """Edge cases for KR auto-update at task completion."""

    def test_kr_not_started_to_in_progress(self, forge_env, project_name):
        """First task done → descriptive KR moves NOT_STARTED → IN_PROGRESS."""
        _s = __import__("pipeline")._get_storage()
        obj_data = {"project": project_name, "updated": "", "objectives": [
            {"id": "O-001", "title": "Test Obj", "status": "ACTIVE",
             "scopes": [], "key_results": [
                 {"id": "KR-1", "description": "Feature complete",
                  "status": "NOT_STARTED"}
             ]}
        ]}
        _s.save_data(project_name, 'objectives', obj_data)

        task = make_task("T-001", "first-task", status="DONE", origin="O-001")
        task2 = make_task("T-002", "second-task", status="TODO", origin="O-001")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task, task2]}
        save_tracker(project_name, tracker)

        _auto_update_kr(project_name, task, tracker)

        obj_reloaded = _s.load_data(project_name, 'objectives')
        kr = obj_reloaded["objectives"][0]["key_results"][0]
        assert kr["status"] == "IN_PROGRESS"

    def test_kr_achieved_when_all_done(self, forge_env, project_name):
        """All tasks done → descriptive KR moves to ACHIEVED."""
        _s = __import__("pipeline")._get_storage()
        obj_data = {"project": project_name, "updated": "", "objectives": [
            {"id": "O-001", "title": "Test Obj", "status": "ACTIVE",
             "scopes": [], "key_results": [
                 {"id": "KR-1", "description": "Feature complete",
                  "status": "IN_PROGRESS"}
             ]}
        ]}
        _s.save_data(project_name, 'objectives', obj_data)

        task = make_task("T-001", "last-task", status="DONE", origin="O-001")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        _auto_update_kr(project_name, task, tracker)

        obj_reloaded = _s.load_data(project_name, 'objectives')
        kr = obj_reloaded["objectives"][0]["key_results"][0]
        assert kr["status"] == "ACHIEVED"
        assert "achieved_at" in kr

    def test_numeric_kr_not_auto_updated(self, forge_env, project_name):
        """Numeric KR should NOT be auto-updated — requires human judgment."""
        _s = __import__("pipeline")._get_storage()
        obj_data = {"project": project_name, "updated": "", "objectives": [
            {"id": "O-001", "title": "Test Obj", "status": "ACTIVE",
             "scopes": [], "key_results": [
                 {"id": "KR-1", "metric": "API endpoints",
                  "baseline": 5, "target": 25, "current": 5}
             ]}
        ]}
        _s.save_data(project_name, 'objectives', obj_data)

        task = make_task("T-001", "api-task", status="DONE", origin="O-001")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task]}
        save_tracker(project_name, tracker)

        _auto_update_kr(project_name, task, tracker)

        obj_reloaded = _s.load_data(project_name, 'objectives')
        kr = obj_reloaded["objectives"][0]["key_results"][0]
        assert kr["current"] == 5  # NOT changed

    def test_kr_update_writes_trace(self, forge_env, project_name, monkeypatch):
        """KR auto-update writes trace entries when debug enabled."""
        _reset_debug(monkeypatch, True)
        _s = __import__("pipeline")._get_storage()

        obj_data = {"project": project_name, "updated": "", "objectives": [
            {"id": "O-001", "title": "Test", "status": "ACTIVE",
             "scopes": [], "key_results": [
                 {"id": "KR-1", "description": "Done",
                  "status": "NOT_STARTED"}
             ]}
        ]}
        _s.save_data(project_name, 'objectives', obj_data)

        task = make_task("T-001", "kr-trace", status="DONE", origin="O-001")
        task2 = make_task("T-002", "kr-trace2", status="TODO", origin="O-001")
        tracker = {"project": project_name, "goal": "Test",
                   "created": "2025-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z",
                   "tasks": [task, task2]}
        save_tracker(project_name, tracker)

        _auto_update_kr(project_name, task, tracker)

        entries = _read_trace(forge_env, project_name)
        kr_changes = [e for e in entries if e.get("event") == "kr_update.change"]
        assert len(kr_changes) == 1
        assert kr_changes[0]["old_status"] == "NOT_STARTED"
        assert kr_changes[0]["new_status"] == "IN_PROGRESS"

        _cleanup_debug()
