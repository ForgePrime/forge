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
    save_tracker,
    load_tracker,
)
from contracts import atomic_write_json
from conftest import make_task


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
        import pipeline
        monkeypatch.setenv("FORGE_DEBUG", "true")
        pipeline._DEBUG_CHECKED = None

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

        trace_file = Path("forge_output") / project_name / "trace.jsonl"
        assert trace_file.exists()

        lines = trace_file.read_text(encoding="utf-8").strip().split("\n")
        events = [json.loads(line)["event"] for line in lines if "event" in json.loads(line)]

        # Should have at least: start, ceremony, reasoning check, gates, ac_start, summary
        assert "complete.start" in events
        assert "complete.ceremony" in events
        assert "complete.check_reasoning" in events
        assert "complete.ac_start" in events

        # Every entry should have timestamp
        for line in lines:
            entry = json.loads(line)
            assert "ts" in entry

        pipeline._DEBUG_CHECKED = None
