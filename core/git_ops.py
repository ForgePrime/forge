"""
Git Workflow — branch, worktree, and PR management for Forge tasks.

Integrates with pipeline to provide automatic branch-per-task workflow:
- Branch creation on task start (pipeline next)
- Worktree creation for parallel multi-agent work
- Push + PR creation on task completion (pipeline complete)
- Cleanup on task completion

Configuration (in pipeline config under git_workflow):
    {
        "git_workflow": {
            "enabled": true,
            "branch_prefix": "forge/",
            "use_worktrees": true,
            "worktree_dir": "forge_worktrees",
            "auto_push": true,
            "auto_pr": true,
            "pr_target": "main",
            "pr_draft": true
        }
    }

Usage:
    python -m core.git_ops status                    Show worktrees and branches
    python -m core.git_ops cleanup {project}         Clean up merged branches/worktrees
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Default configuration
GIT_WORKFLOW_DEFAULTS = {
    "enabled": False,
    "branch_prefix": "forge/",
    "use_worktrees": False,
    "worktree_dir": "forge_worktrees",
    "auto_push": True,
    "auto_pr": True,
    "pr_target": "main",
    "pr_draft": True,
}

VALID_GIT_WORKFLOW_KEYS = set(GIT_WORKFLOW_DEFAULTS.keys())


# -- Helpers --

def slugify(name: str, max_len: int = 40) -> str:
    """Convert task name to branch-safe slug."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug[:max_len].rstrip('-')


def get_branch_name(task_id: str, task_name: str, config: dict) -> str:
    """Build branch name from task ID and name."""
    prefix = config.get("branch_prefix", "forge/")
    slug = slugify(task_name)
    return f"{prefix}{task_id}-{slug}"


def _run_git(*args, cwd=None):
    """Run a git command, return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, encoding="utf-8",
            cwd=cwd,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return False, "", "git not found"


def _run_gh(*args, cwd=None):
    """Run a gh CLI command, return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["gh"] + list(args),
            capture_output=True, text=True, encoding="utf-8",
            cwd=cwd,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return False, "", "gh CLI not found — install from https://cli.github.com/"


def get_repo_root(cwd=None):
    """Get the git repository root directory."""
    ok, out, _ = _run_git("rev-parse", "--show-toplevel", cwd=cwd)
    return out if ok else None


def get_current_branch(cwd=None):
    """Get the current branch name."""
    ok, out, _ = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    return out if ok else None


def branch_exists(branch_name: str, cwd=None) -> bool:
    """Check if a branch exists locally."""
    ok, _, _ = _run_git("rev-parse", "--verify", branch_name, cwd=cwd)
    return ok


# -- Core Operations --

def create_branch(branch_name: str, base_ref: str = "HEAD", cwd=None):
    """Create a new git branch. Returns (success, message)."""
    if branch_exists(branch_name, cwd=cwd):
        return True, f"Branch '{branch_name}' already exists"

    ok, out, err = _run_git("branch", branch_name, base_ref, cwd=cwd)
    if ok:
        return True, f"Created branch '{branch_name}'"
    return False, f"Failed to create branch: {err}"


def checkout_branch(branch_name: str, cwd=None):
    """Switch to a branch. Returns (success, message)."""
    ok, out, err = _run_git("checkout", branch_name, cwd=cwd)
    if ok:
        return True, f"Switched to branch '{branch_name}'"
    return False, f"Failed to checkout: {err}"


def create_worktree(worktree_path: str, branch_name: str, base_ref: str = "HEAD"):
    """Create a git worktree with a new or existing branch.

    Returns (success, message).
    """
    wt = Path(worktree_path)

    if wt.exists():
        ok, _, _ = _run_git("rev-parse", "--git-dir", cwd=str(wt))
        if ok:
            return True, f"Worktree already exists at '{worktree_path}'"
        return False, f"Path '{worktree_path}' exists but is not a worktree"

    wt.parent.mkdir(parents=True, exist_ok=True)

    if branch_exists(branch_name):
        ok, out, err = _run_git("worktree", "add", str(wt), branch_name)
    else:
        ok, out, err = _run_git("worktree", "add", "-b", branch_name, str(wt), base_ref)

    if ok:
        return True, f"Created worktree at '{worktree_path}' on branch '{branch_name}'"
    return False, f"Failed to create worktree: {err}"


def remove_worktree(worktree_path: str, force: bool = False):
    """Remove a git worktree. Returns (success, message)."""
    wt = Path(worktree_path)
    if not wt.exists():
        _run_git("worktree", "prune")
        return True, f"Worktree '{worktree_path}' already removed"

    args = ["worktree", "remove", str(wt)]
    if force:
        args.append("--force")

    ok, out, err = _run_git(*args)
    if ok:
        return True, f"Removed worktree '{worktree_path}'"
    return False, f"Failed to remove worktree: {err}"


def push_branch(branch_name: str, cwd=None):
    """Push branch to origin with upstream tracking. Returns (success, message)."""
    ok, out, err = _run_git("push", "-u", "origin", branch_name, cwd=cwd)
    if ok:
        return True, f"Pushed '{branch_name}' to origin"
    return False, f"Failed to push: {err}"


def create_pr(branch_name: str, title: str, body: str, target: str = "main",
              draft: bool = True, cwd=None):
    """Create a pull request using gh CLI.

    Returns (success, pr_url_or_error).
    """
    args = ["pr", "create",
            "--head", branch_name,
            "--base", target,
            "--title", title,
            "--body", body]
    if draft:
        args.append("--draft")

    ok, out, err = _run_gh(*args, cwd=cwd)
    if ok:
        return True, out  # out is the PR URL

    # Check if PR already exists
    if "already exists" in err.lower():
        ok2, url, _ = _run_gh("pr", "view", branch_name,
                               "--json", "url", "--jq", ".url", cwd=cwd)
        if ok2:
            return True, url

    return False, f"Failed to create PR: {err}"


def list_worktrees():
    """List all git worktrees."""
    ok, out, _ = _run_git("worktree", "list", "--porcelain")
    if not ok:
        return []

    worktrees = []
    current = {}
    for line in out.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:]
        elif line == "bare":
            current["bare"] = True
        elif line == "":
            if current:
                worktrees.append(current)
                current = {}
    if current:
        worktrees.append(current)

    return worktrees


def list_forge_branches(prefix: str = "forge/"):
    """List all branches with the forge prefix."""
    ok, out, _ = _run_git("branch", "--list", f"{prefix}*",
                           "--format=%(refname:short)")
    if not ok:
        return []
    return [b.strip() for b in out.split("\n") if b.strip()]


def delete_branch(branch_name: str, force: bool = False):
    """Delete a local branch. Returns (success, message)."""
    flag = "-D" if force else "-d"
    ok, out, err = _run_git("branch", flag, branch_name)
    if ok:
        return True, f"Deleted branch '{branch_name}'"
    return False, f"Failed to delete branch: {err}"


# -- High-Level Workflow Functions (called by pipeline) --

def get_git_workflow_config(tracker: dict) -> dict:
    """Extract git_workflow config from tracker, with defaults."""
    config = tracker.get("config", {}).get("git_workflow", {})
    result = dict(GIT_WORKFLOW_DEFAULTS)
    result.update(config)
    return result


def validate_git_workflow_config(config: dict) -> list:
    """Validate git_workflow config keys."""
    errors = []
    unknown = set(config.keys()) - VALID_GIT_WORKFLOW_KEYS
    if unknown:
        errors.append(f"Unknown git_workflow keys: {', '.join(sorted(unknown))}")
    if "branch_prefix" in config and not isinstance(config["branch_prefix"], str):
        errors.append("branch_prefix must be a string")
    if "pr_target" in config and not isinstance(config["pr_target"], str):
        errors.append("pr_target must be a string")
    return errors


def on_task_start(project: str, task: dict, config: dict) -> dict:
    """Called by pipeline next — create branch + optional worktree.

    Returns dict with keys: branch, worktree_path (if created).
    """
    result = {}

    if not config.get("enabled"):
        return result

    task_id = task["id"]
    task_name = task["name"]
    branch_name = get_branch_name(task_id, task_name, config)

    if config.get("use_worktrees"):
        # Worktree mode: create branch + worktree together
        repo_root = get_repo_root()
        if not repo_root:
            print(f"  WARNING: Not in a git repo, skipping git workflow",
                  file=sys.stderr)
            return result

        wt_dir = config.get("worktree_dir", "forge_worktrees")
        slug = slugify(task_name)
        wt_path = os.path.join(repo_root, wt_dir, f"{task_id}-{slug}")

        ok, msg = create_worktree(wt_path, branch_name)
        print(f"  Git: {msg}")
        if ok:
            result["branch"] = branch_name
            result["worktree_path"] = wt_path
    else:
        # Branch-only mode: create branch + checkout
        ok, msg = create_branch(branch_name)
        print(f"  Git: {msg}")
        if ok:
            ok2, msg2 = checkout_branch(branch_name)
            print(f"  Git: {msg2}")
            result["branch"] = branch_name

    return result


def on_task_complete(project: str, task: dict, config: dict) -> dict:
    """Called by pipeline complete — push + PR + optional worktree cleanup.

    Returns dict with keys: pr_url, pushed, worktree_removed.
    """
    result = {}

    if not config.get("enabled"):
        return result

    branch_name = task.get("branch")
    if not branch_name:
        return result

    worktree_path = task.get("worktree_path")
    cwd = worktree_path if worktree_path and os.path.isdir(worktree_path) else None

    # Push
    if config.get("auto_push"):
        ok, msg = push_branch(branch_name, cwd=cwd)
        print(f"  Git: {msg}")
        result["pushed"] = ok

        # Create PR
        if ok and config.get("auto_pr"):
            pr_title = f"{task['id']}: {task['name']}"
            pr_body = _build_pr_body(task)
            target = config.get("pr_target", "main")
            draft = config.get("pr_draft", True)

            ok_pr, pr_url = create_pr(branch_name, pr_title, pr_body,
                                       target=target, draft=draft, cwd=cwd)
            if ok_pr:
                print(f"  Git: Created PR -> {pr_url}")
                result["pr_url"] = pr_url
            else:
                print(f"  Git: {pr_url}", file=sys.stderr)

    # Cleanup worktree
    if worktree_path and config.get("use_worktrees"):
        ok, msg = remove_worktree(worktree_path)
        print(f"  Git: {msg}")
        result["worktree_removed"] = ok
    elif not config.get("use_worktrees"):
        # Branch-only mode: checkout back to target branch
        target = config.get("pr_target", "main")
        checkout_branch(target)

    return result


def _build_pr_body(task: dict) -> str:
    """Build PR description from task metadata."""
    lines = []
    lines.append(f"## Task: {task['id']} -- {task['name']}")
    lines.append("")

    if task.get("description"):
        lines.append(task["description"])
        lines.append("")

    if task.get("origin"):
        lines.append(f"**Origin**: {task['origin']}")
    if task.get("scopes"):
        lines.append(f"**Scopes**: {', '.join(task['scopes'])}")

    if task.get("acceptance_criteria"):
        lines.append("")
        lines.append("### Acceptance Criteria")
        for ac in task["acceptance_criteria"]:
            text = ac.get("text", ac) if isinstance(ac, dict) else ac
            lines.append(f"- [ ] {text}")

    lines.append("")
    lines.append("---")
    lines.append("*Created by Forge pipeline*")

    return "\n".join(lines)


# -- CLI Commands --

def cmd_status(args):
    """Show git workflow status — branches and worktrees."""
    print("## Git Workflow Status")
    print()

    # Current branch
    current = get_current_branch()
    if current:
        print(f"Current branch: **{current}**")
        print()

    # Worktrees
    worktrees = list_worktrees()
    if len(worktrees) > 1:
        print(f"### Worktrees ({len(worktrees) - 1} active)")
        for wt in worktrees[1:]:
            branch = wt.get("branch", "detached").replace("refs/heads/", "")
            print(f"  {branch} -> {wt['path']}")
    else:
        print("No active worktrees.")
    print()

    # Forge branches
    branches = list_forge_branches()
    if branches:
        print(f"### Forge Branches ({len(branches)})")
        for b in branches:
            print(f"  {b}")
    else:
        print("No forge branches.")


def cmd_cleanup(args):
    """Clean up branches and worktrees for completed tasks."""
    from storage import JSONFileStorage

    storage = JSONFileStorage()
    if not storage.exists(args.project, "tracker"):
        print(f"No tracker for project '{args.project}'.")
        return

    tracker = storage.load_data(args.project, "tracker")
    done_tasks = [t for t in tracker["tasks"]
                  if t["status"] in ("DONE", "SKIPPED")]

    cleaned_branches = 0
    cleaned_worktrees = 0

    for task in done_tasks:
        branch = task.get("branch")
        wt_path = task.get("worktree_path")

        if wt_path and os.path.isdir(wt_path):
            ok, msg = remove_worktree(wt_path)
            print(f"  {msg}")
            if ok:
                cleaned_worktrees += 1

        if branch and branch_exists(branch):
            ok, msg = delete_branch(branch)
            print(f"  {msg}")
            if ok:
                cleaned_branches += 1

    _run_git("worktree", "prune")

    print(f"\nCleaned: {cleaned_branches} branches, {cleaned_worktrees} worktrees")


def main():
    parser = argparse.ArgumentParser(description="Forge Git Workflow")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show git workflow status")

    p = sub.add_parser("cleanup", help="Clean up completed task branches/worktrees")
    p.add_argument("project", help="Project name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        from errors import PreconditionError
        raise PreconditionError("No command specified")

    commands = {
        "status": cmd_status,
        "cleanup": cmd_cleanup,
    }

    from errors import ForgeError
    try:
        commands[args.command](args)
    except ForgeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
