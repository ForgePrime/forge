"""Git diff verification — cross-check delivery.changes[] against actual filesystem.

Workflow per task:
  BEFORE executor runs:  snapshot_head(workspace) → commit_sha_before
  AFTER delivery:        diff_since(workspace, commit_sha_before) → actual file changes
  Compare actual vs declared (delivery.changes[].file_path) → mismatch report.

Forge initializes workspace as a git repo on first use. Each task creates a
commit so the next task can diff from there.
"""

import subprocess
import pathlib
from dataclasses import dataclass, field


@dataclass
class GitDiffReport:
    workspace_dir: str
    head_before: str | None = None
    head_after: str | None = None
    actual_changes: list[dict] = field(default_factory=list)   # [{"path": ..., "action": A|M|D, "lines_added": N, "lines_removed": N}]
    declared_changes: list[dict] = field(default_factory=list)  # from delivery.changes[]
    undeclared_files: list[str] = field(default_factory=list)   # actually changed but not in delivery
    phantom_files: list[str] = field(default_factory=list)      # in delivery but not actually changed
    summary: str = ""
    has_mismatch: bool = False
    error: str | None = None


def _run_git(workspace_dir: str, args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git"] + args,
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def ensure_repo(workspace_dir: str, initial_author: str = "forge <forge@local>") -> tuple[bool, str]:
    """Ensure workspace is a git repo. Initialize if missing."""
    ws = pathlib.Path(workspace_dir)
    ws.mkdir(parents=True, exist_ok=True)
    if (ws / ".git").exists():
        return True, "repo exists"

    rc, out, err = _run_git(workspace_dir, ["init", "-b", "main"])
    if rc != 0:
        return False, f"git init failed: {err}"

    # Set local user config so commits can be made
    _run_git(workspace_dir, ["config", "user.email", "forge@local"])
    _run_git(workspace_dir, ["config", "user.name", "forge"])

    # Initial empty commit so there's always a HEAD to diff from
    _run_git(workspace_dir, ["commit", "--allow-empty", "-m", "forge: initial"])
    return True, "repo initialized"


def snapshot_head(workspace_dir: str) -> tuple[str | None, str | None]:
    """Return current HEAD sha. None + err if no repo / no commits."""
    rc, out, err = _run_git(workspace_dir, ["rev-parse", "HEAD"])
    if rc != 0:
        return None, err
    return out, None


def commit_all(workspace_dir: str, message: str) -> tuple[str | None, str | None]:
    """Stage and commit all changes. Returns new HEAD sha (or None + err).

    If nothing to commit, returns current HEAD unchanged.
    """
    _run_git(workspace_dir, ["add", "-A"])
    rc, out, err = _run_git(workspace_dir, ["commit", "-m", message])
    if rc != 0 and "nothing to commit" not in (out + err).lower():
        return None, f"commit failed: {err or out}"
    head, head_err = snapshot_head(workspace_dir)
    return head, head_err


def diff_report(
    workspace_dir: str,
    head_before: str,
    declared_changes: list[dict] | None = None,
) -> GitDiffReport:
    """Produce diff report vs head_before. Compare with declared delivery.changes[].

    Actions A=added, M=modified, D=deleted, R=renamed, T=type change.
    """
    report = GitDiffReport(workspace_dir=workspace_dir, head_before=head_before, declared_changes=declared_changes or [])

    # Get current HEAD (after)
    head_after, err = snapshot_head(workspace_dir)
    if not head_after:
        report.error = f"snapshot HEAD failed: {err}"
        return report
    report.head_after = head_after

    # numstat + name-status
    rc, numstat, err_ns = _run_git(workspace_dir, ["diff", "--numstat", f"{head_before}..{head_after}"])
    if rc != 0:
        report.error = f"git diff failed: {err_ns}"
        return report

    rc2, name_status, err_n = _run_git(workspace_dir, ["diff", "--name-status", f"{head_before}..{head_after}"])

    # Build actions map from name-status
    actions: dict[str, str] = {}
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            action = parts[0][0].upper()  # A/M/D/R/T — first char
            path = parts[-1]
            actions[path] = action

    # Build numstat
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_str, removed_str, path = parts[0], parts[1], parts[2]
        try:
            added = int(added_str) if added_str != "-" else None
            removed = int(removed_str) if removed_str != "-" else None
        except ValueError:
            added, removed = None, None
        report.actual_changes.append({
            "path": path,
            "action": actions.get(path, "M"),
            "lines_added": added,
            "lines_removed": removed,
        })

    # Compare
    actual_paths = {c["path"] for c in report.actual_changes}
    declared_paths = {c.get("file_path", "") for c in (declared_changes or []) if c.get("file_path")}
    # Normalize path separators
    actual_norm = {p.replace("\\", "/") for p in actual_paths}
    declared_norm = {p.replace("\\", "/") for p in declared_paths}

    report.undeclared_files = sorted(actual_norm - declared_norm)
    report.phantom_files = sorted(declared_norm - actual_norm)
    report.has_mismatch = bool(report.undeclared_files or report.phantom_files)
    report.summary = (
        f"actual={len(actual_norm)} declared={len(declared_norm)} "
        f"undeclared={len(report.undeclared_files)} phantom={len(report.phantom_files)}"
    )
    return report
