"""Pipeline git operations — commit detection, auto-record changes, branch workflow."""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import _get_storage, _trace, now_iso
from storage import load_json_data


def _get_current_commit() -> str:
    """Get current HEAD commit hash, or empty string if not a git repo."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8"
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def _auto_record_changes(project: str, task_id: str, base_commit: str, reasoning: str,
                          cwd: str = None) -> int:
    """Auto-detect git changes since base_commit and record unrecorded ones.

    Args:
        cwd: Working directory for git commands (e.g. worktree path).
             If None, uses current directory.

    Returns number of new changes recorded.
    """
    import subprocess

    if not base_commit:
        return 0

    # Get files changed between base_commit and HEAD (committed changes)
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", base_commit, "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=cwd,
        )
        committed = result.stdout.strip()
    except FileNotFoundError:
        return 0

    # Also get uncommitted changes
    result2 = subprocess.run(
        ["git", "diff", "--numstat", "HEAD"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=cwd,
    )
    uncommitted = result2.stdout.strip()

    # Merge both (committed takes priority for stats)
    file_stats = {}
    for source in [committed, uncommitted]:
        if not source:
            continue
        for line in source.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, removed, filepath = parts
            if filepath not in file_stats:
                added = int(added) if added != "-" else 0
                removed = int(removed) if removed != "-" else 0
                file_stats[filepath] = (added, removed)

    if not file_stats:
        return 0

    # Load existing changes — skip already recorded files for this task
    storage = _get_storage()
    ch_data = storage.load_data(project, 'changes')

    existing_files = {c["file"] for c in ch_data.get("changes", [])
                      if c.get("task_id") == task_id}

    # Find next C-NNN ID
    existing_ids = [
        int(c["id"].split("-")[1]) for c in ch_data.get("changes", [])
        if c.get("id", "").startswith("C-")
    ]
    next_id = max(existing_ids, default=0) + 1

    timestamp = now_iso()
    new_changes = []

    for filepath, (added, removed) in sorted(file_stats.items()):
        if filepath in existing_files:
            continue

        # Detect action from committed diff
        action = "edit"
        if added > 0 and removed == 0:
            check = subprocess.run(
                ["git", "diff", "--diff-filter=A", "--name-only", base_commit, "HEAD", "--", filepath],
                capture_output=True, text=True, encoding="utf-8",
                cwd=cwd,
            )
            if filepath in check.stdout:
                action = "create"
        elif added == 0 and removed > 0:
            check = subprocess.run(
                ["git", "diff", "--diff-filter=D", "--name-only", base_commit, "HEAD", "--", filepath],
                capture_output=True, text=True, encoding="utf-8",
                cwd=cwd,
            )
            if filepath in check.stdout:
                action = "delete"

        change = {
            "id": f"C-{next_id:03d}",
            "task_id": task_id,
            "file": filepath,
            "action": action,
            "summary": reasoning or "(auto-recorded at completion)",
            "reasoning_trace": [],
            "decision_ids": [],
            "lines_added": added,
            "lines_removed": removed,
            "group_id": task_id,
            "guidelines_checked": [],
            "timestamp": timestamp,
        }
        new_changes.append(change)
        next_id += 1

    if new_changes:
        ch_data["changes"].extend(new_changes)
        storage.save_data(project, 'changes', ch_data)

    return len(new_changes)


def _apply_git_workflow_start(project: str, tracker: dict, task: dict) -> dict:
    """Apply git workflow on task start (branch + optional worktree).

    Returns dict with branch/worktree_path keys, or empty dict if disabled.
    """
    try:
        from git_ops import get_git_workflow_config, on_task_start
    except ImportError:
        return {}

    config = get_git_workflow_config(tracker)
    if not config.get("enabled"):
        return {}

    return on_task_start(project, task, config)


def _apply_git_workflow_complete(project: str, tracker: dict, task: dict) -> dict:
    """Apply git workflow on task complete (push + PR + cleanup).

    Returns dict with pr_url and other result keys, or empty dict if disabled.
    """
    try:
        from git_ops import get_git_workflow_config, on_task_complete
    except ImportError:
        return {}

    config = get_git_workflow_config(tracker)
    if not config.get("enabled"):
        return {}

    return on_task_complete(project, task, config)


def _count_diff_files(base_commit, cwd=None):
    """Count files changed since base_commit."""
    import subprocess as _sp
    if not base_commit:
        return 0
    try:
        result = _sp.run(
            f"git diff --name-only {base_commit}",
            shell=True, capture_output=True, text=True,
            encoding="utf-8", timeout=10, cwd=cwd
        )
        if result.returncode == 0:
            return len([f for f in result.stdout.strip().split("\n") if f.strip()])
    except Exception:
        pass
    return 0
