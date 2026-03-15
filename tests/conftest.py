"""Shared fixtures for Forge test suite."""

import json
import os
import sys
from pathlib import Path

import pytest

# Add core/ to path so we can import modules directly
FORGE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FORGE_ROOT / "core"))


@pytest.fixture
def forge_env(tmp_path, monkeypatch):
    """Set up an isolated forge_output directory.

    Changes cwd to tmp_path so that all modules writing to
    Path("forge_output") / project land inside the temporary directory.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def project_name():
    return "test-project"


@pytest.fixture
def init_project(forge_env, project_name):
    """Create a minimal tracker.json for a project."""
    from pipeline import save_tracker, output_dir

    out = output_dir(project_name)
    out.mkdir(parents=True, exist_ok=True)

    tracker = {
        "project": project_name,
        "goal": "Test goal",
        "created": "2025-01-01T00:00:00Z",
        "updated": "2025-01-01T00:00:00Z",
        "tasks": [],
    }
    save_tracker(project_name, tracker)
    return tracker


def make_task(task_id, name="task", depends_on=None, status="TODO",
              conflicts_with=None, blocked_by_decisions=None,
              acceptance_criteria=None, task_type="feature",
              scopes=None, origin="", parallel=False, exclusions=None):
    """Helper to build a task dict."""
    return {
        "id": task_id,
        "name": name,
        "description": f"Description for {name}",
        "depends_on": depends_on or [],
        "parallel": parallel,
        "conflicts_with": conflicts_with or [],
        "skill": None,
        "instruction": "",
        "acceptance_criteria": acceptance_criteria or [],
        "type": task_type,
        "blocked_by_decisions": blocked_by_decisions or [],
        "scopes": scopes or [],
        "origin": origin,
        "exclusions": exclusions or [],
        "status": status,
        "started_at": None,
        "completed_at": None,
        "failed_reason": None,
    }
