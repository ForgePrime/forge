"""
Pipeline — generic task graph orchestrator.

Evolved from Skill_v1's forge_pipeline.py. Key differences:
- "Project" instead of "Entity" — scope is a goal, not a data entity
- Dynamic task graph — tasks are added by the plan skill, not hardcoded
- No domain-specific logic — pure state machine
- Tasks form a DAG with explicit dependencies
- Tasks support `parallel` and `conflicts_with` metadata (stored, not enforced
  in single-agent mode — designed for future multi-agent orchestration)

State machine per task: TODO -> IN_PROGRESS -> DONE | FAILED | SKIPPED
Subtasks: a task can have child subtasks for batch processing.

Usage:
    python -m core.pipeline <command> <project> [options]

Commands:
    init              {project} --goal "..."        Create project tracker
    add-tasks         {project} --data '{json}'     Add tasks to the graph
    next              {project}                     Get next task/subtask
    complete          {project} {task_id}            Mark task DONE
    fail              {project} {task_id} --reason   Mark task FAILED
    skip              {project} {task_id}            Mark task SKIPPED
    status            {project}                     Dashboard
    list              {project}                     All tasks with status
    reset             {project} --from {task_id}    Reset from task onward
    register-subtasks {project} {task_id} --data    Register subtasks
    complete-subtask  {project} {subtask_id}        Mark subtask DONE
    draft-plan        {project} --data '{json}'     Store draft plan for review
    show-draft        {project}                     Show current draft plan
    approve-plan      {project}                     Approve draft → materialize tasks
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract
from storage import JSONFileStorage, load_json_data, now_iso, tracker_lock
import gates as _gates_mod

CLAIM_WAIT_SECONDS = 1.5

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


# -- Storage --

_default_storage = None

def _get_storage(storage=None):
    """Get storage adapter, using module-level default if not provided."""
    global _default_storage
    if storage is not None:
        return storage
    if _default_storage is None:
        _default_storage = JSONFileStorage()
    return _default_storage


# -- Tracker I/O --

def load_tracker(project: str, storage=None) -> dict:
    s = _get_storage(storage)
    if not s.exists(project, 'tracker'):
        print(f"ERROR: No tracker for project '{project}'. Run: init {project} --goal \"...\"", file=sys.stderr)
        sys.exit(1)
    return s.load_data(project, 'tracker')


def save_tracker(project: str, tracker: dict, storage=None):
    s = _get_storage(storage)
    s.save_data(project, 'tracker', tracker)


def find_task(tracker: dict, task_id: str) -> dict:
    for task in tracker["tasks"]:
        if task["id"] == task_id:
            return task
    print(f"ERROR: Task '{task_id}' not found.", file=sys.stderr)
    sys.exit(1)


def _max_task_num(tasks: list) -> int:
    """Find highest T-NNN number in existing tasks."""
    max_num = 0
    for t in tasks:
        tid = t["id"]
        if tid.startswith("T-") and tid[2:].isdigit():
            max_num = max(max_num, int(tid[2:]))
    return max_num


def _remap_temp_ids(new_tasks: list, existing_tasks: list,
                    update_tasks: list = None) -> dict:
    """Remap temporary IDs (_1, _2, ...) to real T-NNN IDs.

    Returns mapping {temp_id: real_id}.
    Remaps in-place: id, depends_on, conflicts_with in both new_tasks
    and update_tasks. IDs not starting with '_' are left as-is.
    """
    counter = _max_task_num(existing_tasks)
    mapping = {}

    # Assign real IDs to temp IDs
    for t in new_tasks:
        if t["id"].startswith("_"):
            counter += 1
            real_id = f"T-{counter:03d}"
            mapping[t["id"]] = real_id
            t["id"] = real_id

    # Remap references in new_tasks
    for t in new_tasks:
        if "depends_on" in t:
            t["depends_on"] = [mapping.get(d, d) for d in t["depends_on"]]
        if "conflicts_with" in t:
            t["conflicts_with"] = [mapping.get(c, c) for c in t["conflicts_with"]]

    # Remap references in update_tasks
    if update_tasks:
        for u in update_tasks:
            if "depends_on" in u:
                u["depends_on"] = [mapping.get(d, d) for d in u["depends_on"]]
            if "conflicts_with" in u:
                u["conflicts_with"] = [mapping.get(c, c) for c in u["conflicts_with"]]

    return mapping


def validate_dag(tasks: list) -> list:
    """Check for circular dependencies. Returns list of errors."""
    errors = []
    task_ids = {t["id"] for t in tasks}

    # Check all dependencies reference existing tasks
    for t in tasks:
        for dep in t.get("depends_on", []):
            if dep not in task_ids:
                errors.append(f"Task '{t['id']}' depends on unknown task '{dep}'")

    # Simple cycle detection via topological sort attempt
    in_degree = {t["id"]: 0 for t in tasks}
    adj = {t["id"]: [] for t in tasks}
    for t in tasks:
        for dep in t.get("depends_on", []):
            if dep in adj:
                adj[dep].append(t["id"])
                in_degree[t["id"]] += 1

    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    visited = 0
    while queue:
        node = queue.pop(0)
        visited += 1
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited != len(tasks):
        errors.append("Circular dependency detected in task graph")

    # Validate conflicts_with references
    for t in tasks:
        for conflict in t.get("conflicts_with", []):
            if conflict not in task_ids:
                errors.append(f"Task '{t['id']}' conflicts_with unknown task '{conflict}'")

    return errors


# -- Contracts --

CONTRACTS = {
    "add-tasks": {
        "required": ["id", "name"],
        "optional": ["description", "instruction", "depends_on", "parallel",
                      "conflicts_with", "skill", "acceptance_criteria",
                      "type", "blocked_by_decisions", "scopes", "origin",
                      "knowledge_ids", "test_requirements", "alignment",
                      "exclusions", "produces"],
        "enums": {
            "type": {"feature", "bug", "chore", "investigation"},
        },
        "types": {
            "depends_on": list,
            "conflicts_with": list,
            "parallel": bool,
            "acceptance_criteria": list,
            "blocked_by_decisions": list,
            "scopes": list,
            "knowledge_ids": list,
            "test_requirements": dict,
            "alignment": dict,
            "exclusions": list,
            "produces": dict,
        },
        "invariant_texts": [
            "id: task identifier — use temporary IDs (_1, _2, ...) for auto-assignment, or explicit T-NNN. Temp IDs are remapped to T-NNN at materialize time.",
            "name: kebab-case descriptive name (e.g., setup-database-schema)",
            "description: WHAT needs to be done (concrete, not vague)",
            "instruction: HOW to do it (step-by-step, mention specific files)",
            "depends_on: list of prerequisite task IDs — can use temp IDs (_1, _2) within the same batch",
            "parallel: true if this task can run alongside others",
            "conflicts_with: list of task IDs that modify same files — can use temp IDs within the same batch",
            "acceptance_criteria: list of conditions for DONE — supports plain strings or structured: {text, from_template, params}",
            "type: task category — feature (default), bug, chore, or investigation",
            "blocked_by_decisions: list of decision IDs (D-001, etc.) that must be CLOSED before this task can start",
            "scopes: list of guideline scopes this task relates to (e.g., ['backend', 'database']). 'general' is always included automatically.",
            "origin: source of this task — idea ID (I-001) or free text tracing where this task came from",
            "knowledge_ids: list of Knowledge IDs (K-001, etc.) linked to this task for context assembly",
            "test_requirements: {unit: bool, integration: bool, e2e: bool, description: str} — what testing is needed",
            "alignment: dict with {goal, boundaries: {must, must_not, not_in_scope}, success} — persisted alignment contract from planning",
            "exclusions: list of task-specific DO NOT rules — things this task must NOT do (e.g., 'DO NOT modify WorkflowList.tsx', 'DO NOT add error handling — that is T-015')",
            "produces: dict describing what this task creates for downstream consumers — semantic output contracts (e.g., {endpoint: 'POST /users → 201 {id, email}', model: 'User(id, email, name)'}). Shown in pipeline context for dependent tasks.",
            "Batch format: --data '{\"new_tasks\": [...], \"update_tasks\": [...]}' — atomically adds new tasks and updates existing tasks. update_tasks can reference temp IDs from new_tasks in depends_on/conflicts_with.",
        ],
        "example": [
            {
                "id": "_1",
                "name": "setup-database-schema",
                "description": "Create the database schema for user authentication",
                "instruction": "Create migrations/001_auth.sql with users and sessions tables. Follow existing migration patterns.",
                "depends_on": [],
                "parallel": False,
                "type": "feature",
                "scopes": ["database"],
                "acceptance_criteria": [
                    "migrations/001_auth.sql exists with users and sessions tables",
                    "Migration runs without errors on empty database",
                ],
            },
            {
                "id": "_2",
                "name": "implement-auth-middleware",
                "description": "JWT validation middleware",
                "instruction": "Create src/middleware/auth.ts with RS256 JWT validation. Use jsonwebtoken library.",
                "depends_on": ["_1"],
                "parallel": False,
                "conflicts_with": ["_3"],
                "blocked_by_decisions": ["D-001"],
                "type": "feature",
                "acceptance_criteria": [
                    "Middleware rejects requests without valid JWT",
                    "Middleware passes req.user to downstream handlers",
                ],
            },
        ],
    },
    "update-task": {
        "required": ["id"],
        "optional": ["name", "description", "instruction", "depends_on",
                      "conflicts_with", "skill", "acceptance_criteria",
                      "type", "blocked_by_decisions", "scopes", "origin",
                      "knowledge_ids", "test_requirements", "alignment",
                      "exclusions", "produces"],
        "enums": {
            "type": {"feature", "bug", "chore", "investigation"},
        },
        "types": {
            "depends_on": list,
            "conflicts_with": list,
            "acceptance_criteria": list,
            "blocked_by_decisions": list,
            "scopes": list,
            "knowledge_ids": list,
            "test_requirements": dict,
            "alignment": dict,
            "exclusions": list,
            "produces": dict,
        },
        "invariant_texts": [
            "id: existing task ID to update",
            "Only provided fields are updated — omitted fields stay unchanged",
            "Cannot update tasks that are IN_PROGRESS or DONE",
        ],
        "example": [
            {
                "id": "T-002",
                "acceptance_criteria": [
                    "Middleware rejects expired tokens",
                    "Returns 401 with error body on failure",
                ],
                "depends_on": ["T-001", "T-003"],
            },
        ],
    },
    "register-subtasks": {
        "required": ["id"],
        "optional": ["name", "description"],
        "enums": {},
        "types": {},
        "invariant_texts": [
            "id: unique subtask identifier within parent (e.g., S-001)",
            "name: short descriptive name",
            "description: what this subtask does",
            "Subtask IDs are prefixed with parent task ID: T-001/S-001",
            "Parent task must be IN_PROGRESS",
        ],
        "example": [
            {
                "id": "S-001",
                "name": "create-schema-file",
                "description": "Create the SQL migration file with table definitions",
            },
            {
                "id": "S-002",
                "name": "add-indexes",
                "description": "Add performance indexes to the schema",
            },
        ],
    },
    "config": {
        "required": [],
        "optional": ["test_cmd", "lint_cmd", "typecheck_cmd", "branch_prefix",
                      "git_workflow"],
        "enums": {},
        "types": {},
        "invariant_texts": [
            "test_cmd: shell command to run tests (e.g., 'pytest', 'npm test')",
            "lint_cmd: shell command to run linter (e.g., 'ruff check .', 'npm run lint')",
            "typecheck_cmd: shell command for type checking (e.g., 'mypy src/', 'npx tsc --noEmit')",
            "branch_prefix: prefix for git branches (e.g., 'forge/')",
            "git_workflow: nested object for git branch/worktree/PR automation",
            "  git_workflow.enabled: true to activate (default: false)",
            "  git_workflow.branch_prefix: branch name prefix (default: 'forge/')",
            "  git_workflow.use_worktrees: true for worktree-per-task (default: false, uses branch-only)",
            "  git_workflow.worktree_dir: directory for worktrees (default: 'forge_worktrees')",
            "  git_workflow.auto_push: push branch on complete (default: true)",
            "  git_workflow.auto_pr: create PR on complete (default: true)",
            "  git_workflow.pr_target: PR target branch (default: 'main')",
            "  git_workflow.pr_draft: create as draft PR (default: true)",
            "Config is a flat JSON object (except git_workflow which is nested), not an array",
        ],
        "example": [
            {
                "test_cmd": "pytest",
                "lint_cmd": "ruff check .",
                "git_workflow": {
                    "enabled": True,
                    "branch_prefix": "forge/",
                    "use_worktrees": False,
                    "auto_push": True,
                    "auto_pr": True,
                    "pr_target": "main",
                    "pr_draft": True,
                },
            },
        ],
    },
    "draft-plan": {
        "description": "Draft plan wraps an array of tasks (same schema as add-tasks) with metadata about the source objective/idea. "
                       "Stored in tracker.json['draft_plan']. Approve with approve-plan to materialize.",
        "required": ["tasks"],
        "optional": ["idea_id", "objective_id", "assumptions"],
        "types": {
            "tasks": list,
            "assumptions": list,
        },
        "invariant_texts": [
            "tasks: JSON array of task objects — each task follows the add-tasks contract (id, name required; see `pipeline contract add-tasks`)",
            "idea_id: source idea ID (I-NNN) this plan was derived from",
            "objective_id: source objective ID (O-NNN) this plan was derived from",
            "assumptions: optional JSON array of {assumption: str, basis: str, severity: 'HIGH'|'MED'|'LOW'} — readiness gate",
            "If 5+ HIGH-severity assumptions provided, draft is REJECTED (readiness gate fails)",
            "If 3-4 HIGH: warning printed but draft saved",
            "Only ONE draft plan exists at a time — new draft overwrites previous",
            "Draft is NOT materialized until `approve-plan` is called",
            "CLI usage: python -m core.pipeline draft-plan {project} --data '[{tasks}]' [--idea I-NNN] [--objective O-NNN] [--assumptions '[...]']",
            "The --data argument is the tasks array (not the wrapper). idea_id and objective_id are passed as --idea and --objective flags.",
        ],
        "example": [
            {
                "id": "T-010",
                "name": "setup-redis-cache",
                "description": "Configure Redis caching layer",
                "depends_on": [],
                "type": "feature",
                "scopes": ["backend", "infrastructure"],
                "origin": "I-003",
                "acceptance_criteria": [
                    "Redis client configured and connected",
                    "Health check endpoint returns Redis status",
                ],
            },
            {
                "id": "T-011",
                "name": "implement-cache-middleware",
                "description": "Add caching middleware to API routes",
                "depends_on": ["T-010"],
                "type": "feature",
                "scopes": ["backend"],
                "acceptance_criteria": [
                    "GET endpoints cached with 60s TTL",
                    "Cache invalidated on POST/PUT/DELETE",
                ],
            },
        ],
    },
}


# -- Commands --

def cmd_init(args):
    """Create a new project tracker."""
    storage = _get_storage()
    if storage.exists(args.project, 'tracker') and not args.force:
        print(f"Project '{args.project}' already exists.")
        tracker = load_tracker(args.project)
        print_status(args.project, tracker)
        print(f"\nUse --force to overwrite.")
        return

    tracker = {
        "project": args.project,
        "goal": args.goal,
        "created": now_iso(),
        "updated": now_iso(),
        "tasks": [],
    }

    save_tracker(args.project, tracker)

    print(f"## Project created: {args.project}")
    print(f"")
    print(f"Goal: {args.goal}")
    print(f"Saved to: forge_output/{args.project}/tracker.json")
    print(f"")
    print(f"Next: Add tasks with `add-tasks` or run `/plan {args.project}` to decompose the goal.")


def _build_task_entry(t: dict, source_idea_id: str = None, source_objective_id: str = None) -> dict:
    """Build a task entry dict from raw task data. Single source of truth for task schema."""
    entry = {
        "id": t["id"],
        "name": t["name"],
        "description": t.get("description", ""),
        "depends_on": t.get("depends_on", []),
        "parallel": t.get("parallel", False),
        "conflicts_with": t.get("conflicts_with", []),
        "skill": t.get("skill"),
        "instruction": t.get("instruction", ""),
        "acceptance_criteria": t.get("acceptance_criteria", []),
        "type": t.get("type", "feature"),
        "blocked_by_decisions": t.get("blocked_by_decisions", []),
        "scopes": t.get("scopes", []),
        "origin": t.get("origin", source_idea_id or source_objective_id or ""),
        "knowledge_ids": t.get("knowledge_ids", []),
        "alignment": t.get("alignment"),
        "exclusions": t.get("exclusions", []),
        "produces": t.get("produces"),
        "status": "TODO",
        "started_at": None,
        "completed_at": None,
        "failed_reason": None,
    }
    if t.get("test_requirements"):
        entry["test_requirements"] = t["test_requirements"]
    # If origin not set but source_idea_id exists, set it
    if source_idea_id and not entry["origin"]:
        entry["origin"] = source_idea_id
    if source_objective_id and not entry["origin"]:
        entry["origin"] = source_objective_id
    return entry


def cmd_add_tasks(args):
    """Add tasks to the project graph.

    Accepts two formats:
    - Array: [{id: "_1", name: ...}, ...]  (backward compatible, also supports T-NNN)
    - Batch: {new_tasks: [...], update_tasks: [...]}  (atomic add + update)

    Temporary IDs (starting with '_') are auto-remapped to T-NNN.
    """
    try:
        raw_data = load_json_data(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Detect format
    if isinstance(raw_data, dict) and "new_tasks" in raw_data:
        new_tasks = raw_data["new_tasks"]
        update_tasks = raw_data.get("update_tasks", [])
        if not isinstance(new_tasks, list):
            print("ERROR: new_tasks must be a JSON array", file=sys.stderr)
            sys.exit(1)
        if not isinstance(update_tasks, list):
            print("ERROR: update_tasks must be a JSON array", file=sys.stderr)
            sys.exit(1)
    elif isinstance(raw_data, list):
        new_tasks = raw_data
        update_tasks = []
    else:
        print("ERROR: --data must be a JSON array or {new_tasks: [...], update_tasks: [...]}",
              file=sys.stderr)
        sys.exit(1)

    # Contract validation on new_tasks
    errors = validate_contract(CONTRACTS["add-tasks"], new_tasks)
    if errors:
        print(f"ERROR: {len(errors)} validation issues in new_tasks:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    # Validate update_tasks against update-task contract
    if update_tasks:
        for upd in update_tasks:
            errs = validate_contract(CONTRACTS["update-task"], [upd])
            if errs:
                print(f"ERROR: Validation issues in update_tasks for '{upd.get('id', '?')}':",
                      file=sys.stderr)
                for e in errs[:5]:
                    print(f"  {e}", file=sys.stderr)
                sys.exit(1)

    # Atomic section: lock → load → remap → validate → save
    with tracker_lock(args.project):
        tracker = load_tracker(args.project)

        # Remap temporary IDs
        mapping = _remap_temp_ids(new_tasks, tracker["tasks"], update_tasks)

        # Check for duplicate IDs (after remap)
        existing_ids = {t["id"] for t in tracker["tasks"]}
        for t in new_tasks:
            if t["id"] in existing_ids:
                print(f"ERROR: Duplicate task ID '{t['id']}'", file=sys.stderr)
                sys.exit(1)

        # Build task entries
        entries = [_build_task_entry(t) for t in new_tasks]

        # Apply updates to existing tasks
        updatable = ["name", "description", "instruction", "depends_on",
                     "conflicts_with", "skill", "acceptance_criteria",
                     "type", "blocked_by_decisions", "scopes", "origin",
                     "knowledge_ids", "test_requirements"]
        updated_ids = []
        for upd in update_tasks:
            task = find_task(tracker, upd["id"])
            if task["status"] in ("IN_PROGRESS", "DONE"):
                print(f"ERROR: Cannot update task {upd['id']} — status is {task['status']}.",
                      file=sys.stderr)
                sys.exit(1)
            for field in updatable:
                if field in upd:
                    task[field] = upd[field]
            updated_ids.append(upd["id"])

        # Validate DAG with all tasks (existing + new)
        all_tasks = tracker["tasks"] + entries
        dag_errors = validate_dag(all_tasks)
        if dag_errors:
            print(f"ERROR: Task graph validation failed:", file=sys.stderr)
            for e in dag_errors:
                print(f"  {e}", file=sys.stderr)
            sys.exit(1)

        tracker["tasks"].extend(entries)
        save_tracker(args.project, tracker)

    # Print ID mapping
    if mapping:
        print("ID mapping:")
        for temp, real in sorted(mapping.items()):
            print(f"  {temp} -> {real}")

    print(f"Added {len(entries)} tasks to '{args.project}'")
    if updated_ids:
        print(f"Updated {len(updated_ids)} existing tasks: {', '.join(updated_ids)}")
    print_task_list(tracker)
    print(f"\nRun `next {args.project}` to start.")


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


def _get_active_ids(tracker: dict) -> set:
    """IDs of tasks that are CLAIMING or IN_PROGRESS."""
    return {t["id"] for t in tracker["tasks"]
            if t["status"] in ("CLAIMING", "IN_PROGRESS")}


def _has_conflict(task: dict, active_ids: set) -> bool:
    """Check if task conflicts with any active task."""
    conflicts = set(task.get("conflicts_with", []))
    return bool(conflicts & active_ids)


def _load_open_decision_ids(project: str) -> set:
    """Load set of OPEN decision IDs from decisions.json."""
    storage = _get_storage()
    data = storage.load_data(project, 'decisions')
    return {d["id"] for d in data.get("decisions", []) if d.get("status") == "OPEN"}


def _blocked_by_open_decisions(task: dict, open_decision_ids: set) -> list:
    """Return list of OPEN decision IDs that block this task."""
    required = set(task.get("blocked_by_decisions", []))
    if not required:
        return []
    return sorted(required & open_decision_ids)


def _claim_with_retry(args, candidate, agent, max_retries=5):
    """Two-phase claim protocol with retry limit for multi-agent mode."""
    for attempt in range(max_retries):
        tracker = load_tracker(args.project)
        task = find_task(tracker, candidate["id"])

        # Phase 1: CLAIMING
        task["status"] = "CLAIMING"
        task["agent"] = agent
        task["claimed_at"] = now_iso()
        save_tracker(args.project, tracker)

        # Wait
        time.sleep(CLAIM_WAIT_SECONDS)

        # Phase 2: Verify claim
        tracker = load_tracker(args.project)
        task = find_task(tracker, candidate["id"])

        if task["status"] == "CLAIMING" and task.get("agent") == agent:
            # Claim won — promote to IN_PROGRESS
            task["status"] = "IN_PROGRESS"
            task["started_at"] = now_iso()
            task["started_at_commit"] = _get_current_commit()

            # Git workflow: create branch + optional worktree
            git_result = _apply_git_workflow_start(args.project, tracker, task)
            if git_result:
                task.update(git_result)

            save_tracker(args.project, tracker)

            print(f"## Next task: {task['id']} — {task['name']}")
            print(f"Agent: {agent}")
            print(f"Status: TODO -> CLAIMING -> **IN_PROGRESS**")
            if task.get("branch"):
                print(f"Branch: `{task['branch']}`")
            if task.get("worktree_path"):
                print(f"Worktree: `{task['worktree_path']}`")
            print()
            print_task_detail(task)
            return task

        # Claim lost — find next candidate
        print(f"  Claim conflict on {candidate['id']} (attempt {attempt + 1}/{max_retries})",
              file=sys.stderr)

        done_ids = {t["id"] for t in tracker["tasks"]
                    if t["status"] in ("DONE", "SKIPPED")}
        active_ids = _get_active_ids(tracker)
        open_decisions = _load_open_decision_ids(args.project)

        candidate = None
        for t in tracker["tasks"]:
            if t["status"] != "TODO":
                continue
            if not all(dep in done_ids for dep in t["depends_on"]):
                continue
            if _has_conflict(t, active_ids):
                continue
            if _blocked_by_open_decisions(t, open_decisions):
                continue
            candidate = t
            break

        if not candidate:
            print(f"No available tasks after claim conflict.", file=sys.stderr)
            return

    print(f"All tasks contended after {max_retries} attempts. Try again later.",
          file=sys.stderr)
    sys.exit(1)


def cmd_next(args):
    """Get next TODO task with two-phase claim for multi-agent safety.

    Protocol:
    1. Agent writes CLAIMING + agent_name to task
    2. Agent waits CLAIM_WAIT_SECONDS
    3. Agent re-reads tracker — if still own name, set IN_PROGRESS
    4. If another agent overwrote, back off and try next task

    This detects concurrent claims without locks or databases.
    """
    agent = getattr(args, "agent", None) or "default"
    tracker = load_tracker(args.project)

    if not tracker["tasks"]:
        print(f"## No tasks in project '{args.project}'")
        print(f"\nAdd tasks with `add-tasks` or run `/plan {args.project}`")
        return None

    done_ids = {t["id"] for t in tracker["tasks"]
                if t["status"] in ("DONE", "SKIPPED")}
    active_ids = _get_active_ids(tracker)

    # Check if THIS agent already has a task IN_PROGRESS
    for task in tracker["tasks"]:
        if task["status"] == "IN_PROGRESS" and task.get("agent") == agent:
            if task.get("has_subtasks"):
                _next_subtask(args.project, tracker, task)
                return task
            print(f"## Current task: {task['id']} — {task['name']}")
            print(f"Agent: {agent}")
            print(f"Status: **IN_PROGRESS** (started: {task['started_at']})")
            print()
            print_task_detail(task)
            return task

    # Check if ANY task is IN_PROGRESS without an agent (single-agent compat)
    for task in tracker["tasks"]:
        if task["status"] == "IN_PROGRESS" and not task.get("agent"):
            if task.get("has_subtasks"):
                _next_subtask(args.project, tracker, task)
                return task
            print(f"## Current task: {task['id']} — {task['name']}")
            print(f"Status: **IN_PROGRESS** (started: {task['started_at']})")
            print()
            print_task_detail(task)
            return task

    # Find next TODO with deps met, no conflicts, and no blocking decisions
    open_decisions = _load_open_decision_ids(args.project)
    candidate = None
    blocked_by_dec_tasks = []
    for task in tracker["tasks"]:
        if task["status"] != "TODO":
            continue
        deps_met = all(dep in done_ids for dep in task["depends_on"])
        if not deps_met:
            continue
        if _has_conflict(task, active_ids):
            continue
        blocking_decs = _blocked_by_open_decisions(task, open_decisions)
        if blocking_decs:
            blocked_by_dec_tasks.append((task, blocking_decs))
            continue
        candidate = task
        break

    if not candidate:
        # Check terminal states
        all_done = all(t["status"] in ("DONE", "SKIPPED") for t in tracker["tasks"])
        if all_done:
            print(f"## Project complete: {args.project}")
            print()
            print(f"All {len(tracker['tasks'])} tasks finished.")
            print_status(args.project, tracker)
        else:
            failed = [t for t in tracker["tasks"] if t["status"] == "FAILED"]
            blocked_by_conflict = any(
                t["status"] == "TODO"
                and all(dep in done_ids for dep in t["depends_on"])
                and _has_conflict(t, active_ids)
                for t in tracker["tasks"]
            )
            if failed:
                print(f"## Project blocked: {args.project}")
                print()
                for t in failed:
                    print(f"  FAILED: {t['id']} {t['name']}: {t['failed_reason']}")
            elif blocked_by_dec_tasks:
                print(f"## Tasks blocked by OPEN decisions")
                print()
                for t, decs in blocked_by_dec_tasks:
                    print(f"  {t['id']} {t['name']} — blocked by: {', '.join(decs)}")
                print()
                print(f"Resolve with `/decide` or: python -m core.decisions update {args.project} --data '[...]'")
            elif blocked_by_conflict:
                print(f"## All available tasks conflict with active tasks")
                print(f"Agent: {agent}")
                print(f"Active: {', '.join(active_ids)}")
                print(f"Wait for active tasks to complete.")
            else:
                print(f"## No tasks available (dependencies not met)")
                print_status(args.project, tracker)
        return None

    # --- Check if other agents are active ---
    other_agents = {t.get("agent") for t in tracker["tasks"]
                    if t["status"] in ("CLAIMING", "IN_PROGRESS")
                    and t["id"] != candidate["id"]
                    and t.get("agent") and t.get("agent") != agent}

    if not other_agents:
        # Single agent — skip claim protocol, go directly to IN_PROGRESS
        candidate["status"] = "IN_PROGRESS"
        candidate["agent"] = agent
        candidate["started_at"] = now_iso()
        candidate["started_at_commit"] = _get_current_commit()

        # Git workflow: create branch + optional worktree
        git_result = _apply_git_workflow_start(args.project, tracker, candidate)
        if git_result:
            candidate.update(git_result)

        save_tracker(args.project, tracker)

        print(f"## Next task: {candidate['id']} — {candidate['name']}")
        print(f"Agent: {agent}")
        print(f"Status: TODO -> **IN_PROGRESS**")
        if candidate.get("branch"):
            print(f"Branch: `{candidate['branch']}`")
        if candidate.get("worktree_path"):
            print(f"Worktree: `{candidate['worktree_path']}`")
        print()
        print_task_detail(candidate)
        return candidate
    else:
        # Multi-agent — use two-phase claim protocol
        return _claim_with_retry(args, candidate, agent, max_retries=5)


def cmd_begin(args):
    """Combined next + context: claim task and show full execution context.

    Calls cmd_next to claim/resume a task, then immediately prints
    the full context (dependencies, guidelines, knowledge, risks, etc.).
    Equivalent to running ``pipeline next`` followed by ``pipeline context``,
    but in a single invocation.
    """
    task = cmd_next(args)

    if not task or task.get("has_subtasks"):
        return

    print()
    print("---")
    print()

    class _CtxArgs:
        pass
    ctx_args = _CtxArgs()
    ctx_args.project = args.project
    ctx_args.task_id = task["id"]
    ctx_args.lean = getattr(args, "lean", False)
    cmd_context(ctx_args)


def _verify_acceptance_criteria(task):
    """Mechanically verify structured acceptance criteria.

    AC can be:
    - Plain string: treated as verification='manual' (needs --ac-reasoning)
    - Structured dict: {text, verification: 'test'|'command'|'manual', test_path?, command?}

    Returns (results, has_mechanical) where:
    - results: list of {text, verification, passed, output} for mechanical AC
    - has_mechanical: True if any AC has test/command verification
    """
    import subprocess as _sp

    ac_list = task.get("acceptance_criteria", [])
    results = []
    has_mechanical = False

    for ac in ac_list:
        if isinstance(ac, str):
            continue  # Plain string = manual, handled by --ac-reasoning

        if not isinstance(ac, dict):
            continue

        verification = ac.get("verification", "manual")
        text = ac.get("text", str(ac))

        if verification == "manual":
            continue

        has_mechanical = True

        if verification == "test":
            test_path = ac.get("test_path", "")
            if not test_path:
                results.append({"text": text, "verification": "test",
                                "passed": False, "output": "No test_path specified"})
                continue
            try:
                result = _sp.run(
                    f"pytest {test_path} -x -q",
                    shell=True, capture_output=True, text=True,
                    encoding="utf-8", timeout=120
                )
                results.append({"text": text, "verification": "test",
                                "passed": result.returncode == 0,
                                "output": (result.stdout + result.stderr)[:500]})
            except _sp.TimeoutExpired:
                results.append({"text": text, "verification": "test",
                                "passed": False, "output": "Test timed out (120s)"})

        elif verification == "command":
            command = ac.get("command", "")
            if not command:
                results.append({"text": text, "verification": "command",
                                "passed": False, "output": "No command specified"})
                continue
            try:
                result = _sp.run(
                    command, shell=True, capture_output=True, text=True,
                    encoding="utf-8", timeout=120
                )
                results.append({"text": text, "verification": "command",
                                "passed": result.returncode == 0,
                                "output": (result.stdout + result.stderr)[:500]})
            except _sp.TimeoutExpired:
                results.append({"text": text, "verification": "command",
                                "passed": False, "output": "Command timed out (120s)"})

    return results, has_mechanical


def _check_gates_before_complete(project, task_id, task, tracker, force):
    """Mechanically enforce gate checks before task completion.

    - If --force and task type is chore/investigation: bypass gates entirely
    - If --force and task type is feature/bug: reject (gates are mandatory)
    - If gates not configured: pass (nothing to check)
    - If gate_results missing: auto-run gates
    - If required gates failed: exit(1)
    """
    task_type = task.get("type", "feature")
    force_exempt_types = ("chore", "investigation")

    if force and task_type in force_exempt_types:
        return  # --force allowed for chore/investigation

    gates_config = tracker.get("gates", [])
    if not gates_config:
        return  # No gates configured

    if force and task_type not in force_exempt_types:
        print(f"ERROR: --force cannot bypass gates for {task_type} tasks. "
              f"Fix gate failures first.", file=sys.stderr)
        sys.exit(1)

    # Auto-run gates if not yet run
    gate_results = task.get("gate_results", {})
    if not gate_results:
        print(f"  Running gates before completion...")
        _ns = type("NS", (), {"project": project, "task": task_id})()
        all_passed = _gates_mod.cmd_check(_ns)
        # Reload tracker since cmd_check may have saved results
        tracker_reloaded = load_tracker(project)
        for t in tracker_reloaded.get("tasks", []):
            if t["id"] == task_id:
                task.update(t)
                break
        gate_results = task.get("gate_results", {})

    if not gate_results.get("all_passed", True):
        required_gates = {gc["name"] for gc in gates_config if gc.get("required", True)}
        failed = [g["name"] for g in gate_results.get("results", [])
                  if not g.get("passed")]
        required_failed = [name for name in failed if name in required_gates]
        if required_failed:
            print(f"ERROR: Required gates failed: {', '.join(required_failed)}. "
                  f"Fix issues and re-run gates.", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"  Advisory gates failed: {', '.join(failed)} (non-blocking).")


def _determine_ceremony_level(task, diff_file_count=0):
    """Auto-detect ceremony level based on task type and complexity.

    Returns: 'MINIMAL', 'LIGHT', 'STANDARD', or 'FULL'
    - MINIMAL: chore/investigation — reasoning optional, AC not required, --force allowed
    - LIGHT: bug with <= 3 files — reasoning required, AC not required
    - STANDARD: feature with <= 3 AC — reasoning + AC reasoning required
    - FULL: everything else — all checks required
    """
    task_type = task.get("type", "feature")
    ac_count = len(task.get("acceptance_criteria", []))

    if task_type in ("chore", "investigation"):
        return "MINIMAL"
    if task_type == "bug" and diff_file_count <= 3:
        return "LIGHT"
    if task_type == "feature" and ac_count <= 3:
        return "STANDARD"
    return "FULL"


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


def cmd_complete(args):
    """Mark task as DONE."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)
    agent = getattr(args, "agent", None)
    force = getattr(args, "force", False)
    reasoning = getattr(args, "reasoning", None) or ""

    # Determine ceremony level
    base_commit = task.get("started_at_commit", "")
    git_cwd = task.get("worktree_path")
    if git_cwd and not os.path.isdir(git_cwd):
        git_cwd = None
    diff_count = _count_diff_files(base_commit, cwd=git_cwd)
    ceremony = _determine_ceremony_level(task, diff_count)
    print(f"  Ceremony level: {ceremony} ({task.get('type', 'feature')}, {diff_count} files changed)")

    # Verify agent ownership if task was claimed
    if task.get("agent") and agent and task["agent"] != agent:
        print(f"WARNING: Task {args.task_id} is owned by agent '{task['agent']}', "
              f"not '{agent}'. Completing anyway.", file=sys.stderr)

    # Check blocked_by_decisions are resolved
    if not force:
        open_decisions = _load_open_decision_ids(args.project)
        blocking = _blocked_by_open_decisions(task, open_decisions)
        if blocking:
            print(f"WARNING: Task {args.task_id} has OPEN blocking decisions: "
                  f"{', '.join(blocking)}. Close them first or use --force.",
                  file=sys.stderr)
            sys.exit(1)

    # Check reasoning (required for LIGHT, STANDARD, FULL)
    if not force and ceremony not in ("MINIMAL",) and not reasoning.strip():
        print(f"WARNING: --reasoning is required for {ceremony} ceremony level.",
              file=sys.stderr)
        sys.exit(1)

    # Auto-record changes from git before checking
    if base_commit:
        auto_count = _auto_record_changes(args.project, args.task_id, base_commit,
                                           reasoning, cwd=git_cwd)
        if auto_count:
            print(f"  Auto-recorded {auto_count} change(s) from git.")

    # Check that changes were recorded for this task (skip for MINIMAL/LIGHT)
    if not force and ceremony not in ("MINIMAL", "LIGHT"):
        storage = _get_storage()
        changes_data = storage.load_data(args.project, 'changes')
        task_changes = [c for c in changes_data.get("changes", [])
                        if c.get("task_id") == args.task_id]
        if not task_changes:
            print(f"WARNING: No changes recorded for {args.task_id}. "
                  f"Use --force to complete anyway.", file=sys.stderr)
            sys.exit(1)

    # Check that gates passed (mechanical enforcement)
    _check_gates_before_complete(args.project, args.task_id, task, tracker, force)

    # --- Mechanical AC verification: ALWAYS runs regardless of ceremony level ---
    # Mechanical AC (verification: "test"|"command") is not ceremony — it's a gate.
    # If you defined a command to verify AC, it runs. Period.
    ac = task.get("acceptance_criteria", [])
    if ac:
        ac_results, has_mechanical = _verify_acceptance_criteria(task)
        if has_mechanical:
            failed_ac = [r for r in ac_results if not r["passed"]]
            if ac_results:
                print(f"  AC Verification ({len(ac_results)} mechanical):")
                for r in ac_results:
                    status = "PASS" if r["passed"] else "FAIL"
                    print(f"    [{status}] {r['text']} ({r['verification']})")
                    if not r["passed"]:
                        for line in r["output"].split("\n")[:3]:
                            if line.strip():
                                print(f"           {line.strip()}")
            if failed_ac:
                print(f"\nERROR: {len(failed_ac)} mechanical AC verification(s) failed. "
                      f"Fix and retry.", file=sys.stderr)
                sys.exit(1)
            task["ac_verification_results"] = ac_results

    # --- Manual AC reasoning: required for STANDARD/FULL ceremony ---
    if not force and ceremony not in ("MINIMAL", "LIGHT") and ac:
        manual_ac = [c for c in ac if isinstance(c, str) or
                     (isinstance(c, dict) and c.get("verification", "manual") == "manual")]
        if manual_ac:
            ac_reasoning = getattr(args, "ac_reasoning", None)
            if not ac_reasoning:
                print(f"ERROR: Task {args.task_id} has {len(manual_ac)} manual acceptance criteria "
                      f"but no --ac-reasoning provided.", file=sys.stderr)
                print(f"  Manual criteria:", file=sys.stderr)
                for i, criterion in enumerate(manual_ac, 1):
                    text = criterion if isinstance(criterion, str) else criterion.get("text", str(criterion))
                    print(f"    {i}. {text}", file=sys.stderr)
                print(f"  Provide --ac-reasoning with concrete evidence (min 50 chars) for each criterion.",
                      file=sys.stderr)
                sys.exit(1)
            if len(ac_reasoning.strip()) < 50:
                print(f"ERROR: --ac-reasoning too short ({len(ac_reasoning.strip())} chars). "
                      f"Minimum 50 characters required. Provide concrete evidence, "
                      f"not just 'done' or 'verified'.", file=sys.stderr)
                sys.exit(1)
            task["ac_reasoning"] = ac_reasoning
            # Validate AC reasoning quality (blocking, not advisory)
            ac_warnings = _validate_ac_reasoning(ac_reasoning, ac)
            if ac_warnings:
                print(f"**AC REASONING ISSUES** ({len(ac_warnings)}):", file=sys.stderr)
                for w in ac_warnings:
                    print(w, file=sys.stderr)
                print("Each criterion needs evidence: 'AC N: [criterion] — PASS: [concrete proof]'",
                      file=sys.stderr)
                sys.exit(1)

    # Process deferred items — auto-create OPEN decisions
    # Required for STANDARD/FULL: agent must explicitly state what's covered vs deferred
    deferred_raw = getattr(args, "deferred", None)
    has_ac = bool(task.get("acceptance_criteria"))
    if not deferred_raw and not force and ceremony in ("STANDARD", "FULL") and has_ac:
        print(f"WARNING: --deferred required for {ceremony} ceremony with acceptance criteria. "
              f"Pass --deferred '[]' if all source requirements are covered, "
              f"or list deferred items.", file=sys.stderr)
        sys.exit(1)
    if deferred_raw:
        try:
            deferred_items = load_json_data(deferred_raw)
        except (json.JSONDecodeError, Exception):
            print("WARNING: Invalid --deferred JSON, skipping.", file=sys.stderr)
            deferred_items = []

        if isinstance(deferred_items, list) and deferred_items:
            _s = _get_storage()
            dec_data = _s.load_data(args.project, 'decisions')
            decisions = dec_data.get("decisions", [])
            next_id = max((int(d["id"].split("-")[1]) for d in decisions if d.get("id", "").startswith("D-")), default=0) + 1

            created_ids = []
            for item in deferred_items:
                if not isinstance(item, dict) or "requirement" not in item:
                    continue
                dec_id = f"D-{next_id:03d}"
                dec = {
                    "id": dec_id,
                    "task_id": args.task_id,
                    "type": "implementation",
                    "issue": f"DEFERRED: {item['requirement']}",
                    "recommendation": item.get("reason", "Deferred — needs clarification or separate task"),
                    "reasoning": f"Identified during completion of {args.task_id}. Source requirement not implemented in this task.",
                    "status": "OPEN",
                    "decided_by": "claude",
                    "confidence": "HIGH",
                    "timestamp": now_iso(),
                }
                if item.get("affects"):
                    dec["affects"] = item["affects"]
                decisions.append(dec)
                created_ids.append(dec_id)
                next_id += 1

            dec_data["decisions"] = decisions
            _s.save_data(args.project, 'decisions', dec_data)
            task["deferred_decisions"] = created_ids
            print(f"  Deferred: {len(created_ids)} item(s) → OPEN decisions {', '.join(created_ids)}")

    # Git workflow: push + PR + cleanup
    git_result = _apply_git_workflow_complete(args.project, tracker, task)
    if git_result:
        task.update(git_result)

    task["status"] = "DONE"
    task["completed_at"] = now_iso()
    task["ceremony_level"] = ceremony
    save_tracker(args.project, tracker)

    done_count = sum(1 for t in tracker["tasks"] if t["status"] in ("DONE", "SKIPPED"))
    total = len(tracker["tasks"])
    print(f"Task {args.task_id} ({task['name']}): -> DONE  [{done_count}/{total}]")

    # KR auto-update: trace task → origin → objective, update descriptive KRs
    _auto_update_kr(args.project, task, tracker)


def _auto_update_kr(project: str, task: dict, tracker: dict):
    """Auto-update objective KRs after task completion.

    - Descriptive KRs: NOT_STARTED → IN_PROGRESS when first task done,
      → ACHIEVED when ALL tasks for this objective are done.
    - Numeric KRs: not auto-updated (require human judgment).
    - Logs what changed.
    """
    origin = task.get("origin", "")
    _s = _get_storage()
    obj_ids = set()

    if origin.startswith("O-"):
        obj_ids.add(origin)
    elif origin.startswith("I-"):
        if _s.exists(project, 'ideas'):
            ideas_data = _s.load_data(project, 'ideas')
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == origin:
                    obj_ids = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                    break

    if not obj_ids or not _s.exists(project, 'objectives'):
        return

    obj_data = _s.load_data(project, 'objectives')
    all_tasks = tracker.get("tasks", [])
    changed = False

    for obj in obj_data.get("objectives", []):
        if obj["id"] not in obj_ids or obj.get("status") != "ACTIVE":
            continue

        # Count tasks linked to this objective
        obj_tasks = [t for t in all_tasks if t.get("origin") == obj["id"]]
        done_tasks = [t for t in obj_tasks if t["status"] in ("DONE", "SKIPPED")]
        all_done = len(obj_tasks) > 0 and len(done_tasks) == len(obj_tasks)

        print(f"\n  Objective {obj['id']}: {obj['title']}  [{len(done_tasks)}/{len(obj_tasks)} tasks]")

        for kr in obj.get("key_results", []):
            # Numeric KRs: show progress, don't auto-update
            target = kr.get("target")
            if target is not None:
                baseline = kr.get("baseline", 0)
                current = kr.get("current", baseline)
                pct = _objective_kr_pct(baseline, target, current)
                print(f"    {kr['id']}: {current}/{target} ({pct}%) — update manually if changed")
                continue

            # Descriptive KRs: auto-update status
            old_status = kr.get("status", "NOT_STARTED")
            if all_done and old_status != "ACHIEVED":
                kr["status"] = "ACHIEVED"
                kr["achieved_at"] = now_iso()
                kr["achieved_by_task"] = task["id"]
                print(f"    {kr['id']}: {old_status} → ACHIEVED (all {len(obj_tasks)} tasks done)")
                changed = True
            elif not all_done and old_status == "NOT_STARTED" and len(done_tasks) > 0:
                kr["status"] = "IN_PROGRESS"
                kr["started_by_task"] = task["id"]
                print(f"    {kr['id']}: NOT_STARTED → IN_PROGRESS ({len(done_tasks)}/{len(obj_tasks)} tasks done)")
                changed = True
            else:
                print(f"    {kr['id']}: {old_status}")

        obj["updated"] = now_iso()

    if changed:
        obj_data["updated"] = now_iso()
        _s.save_data(project, 'objectives', obj_data)
        print(f"  KR progress saved.")


def cmd_fail(args):
    """Mark task as FAILED."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)

    task["status"] = "FAILED"
    task["failed_reason"] = args.reason or "Unknown error"
    task["completed_at"] = now_iso()
    save_tracker(args.project, tracker)
    print(f"Task {args.task_id} ({task['name']}): -> FAILED -- {task['failed_reason']}")


def cmd_skip(args):
    """Mark task as SKIPPED. Requires --reason. Feature/bug tasks also require --force."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)
    reason = getattr(args, "reason", None) or ""
    force = getattr(args, "force", False)

    if not reason.strip():
        print(f"ERROR: --reason is required when skipping a task. "
              f"Explain why this task cannot be completed.", file=sys.stderr)
        sys.exit(1)

    if len(reason.strip()) < 50:
        print(f"ERROR: --reason too short ({len(reason.strip())} chars). "
              f"Minimum 50 characters. Provide a real explanation, not a placeholder.",
              file=sys.stderr)
        sys.exit(1)

    task_type = task.get("type", "feature")
    if task_type in ("feature", "bug") and not force:
        print(f"ERROR: Cannot skip {task_type} task {args.task_id} without --force. "
              f"Feature and bug tasks represent committed deliverables. "
              f"Use --force --reason '...' to confirm this is intentional.",
              file=sys.stderr)
        sys.exit(1)

    task["status"] = "SKIPPED"
    task["skip_reason"] = reason.strip()
    task["completed_at"] = now_iso()
    save_tracker(args.project, tracker)

    done_count = sum(1 for t in tracker["tasks"] if t["status"] in ("DONE", "SKIPPED"))
    total = len(tracker["tasks"])
    print(f"Task {args.task_id} ({task['name']}): -> SKIPPED  [{done_count}/{total}]")
    print(f"  Reason: {reason.strip()}")


def cmd_status(args):
    """Dashboard."""
    tracker = load_tracker(args.project)
    print_status(args.project, tracker)


def cmd_list(args):
    """All tasks with status."""
    tracker = load_tracker(args.project)
    print(f"## Project: {args.project}")
    print(f"Goal: {tracker.get('goal', '(none)')}")
    print(f"")
    print_task_list(tracker)


def cmd_reset(args):
    """Reset from task onward to TODO."""
    tracker = load_tracker(args.project)

    start_idx = None
    for i, task in enumerate(tracker["tasks"]):
        if task["id"] == args.from_task:
            start_idx = i
            break

    if start_idx is None:
        print(f"ERROR: Task '{args.from_task}' not found.", file=sys.stderr)
        sys.exit(1)

    # Collect IDs being reset
    reset_ids = {t["id"] for t in tracker["tasks"][start_idx:]}

    # Also reset any task that depends on a reset task (cascade)
    changed = True
    while changed:
        changed = False
        for task in tracker["tasks"]:
            if task["id"] not in reset_ids:
                if any(dep in reset_ids for dep in task.get("depends_on", [])):
                    reset_ids.add(task["id"])
                    changed = True

    reset_count = 0
    for task in tracker["tasks"]:
        if task["id"] in reset_ids:
            task["status"] = "TODO"
            task["started_at"] = None
            task["completed_at"] = None
            task["failed_reason"] = None
            if task.get("has_subtasks"):
                task["has_subtasks"] = False
                task["subtask_total"] = 0
                task["subtask_done"] = 0
                task.pop("subtasks", None)
            reset_count += 1

    save_tracker(args.project, tracker)
    print(f"Reset {reset_count} tasks (from {args.from_task} + dependents) to TODO.")
    print_task_list(tracker)


def cmd_update_task(args):
    """Update fields of an existing task."""
    try:
        updates = load_json_data(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(updates, dict):
        print("ERROR: --data must be a JSON object", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["update-task"], [updates])
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    # Atomic section: lock → load → update → validate → save
    with tracker_lock(args.project):
        tracker = load_tracker(args.project)
        task = find_task(tracker, updates["id"])

        if task["status"] in ("IN_PROGRESS", "DONE"):
            print(f"ERROR: Cannot update task {updates['id']} — status is {task['status']}. "
                  f"Reset it first.", file=sys.stderr)
            sys.exit(1)

        # Apply updates (only provided fields)
        updatable = ["name", "description", "instruction", "depends_on",
                     "conflicts_with", "skill", "acceptance_criteria",
                     "type", "blocked_by_decisions", "scopes", "origin",
                     "knowledge_ids", "test_requirements"]
        changed = []
        for field in updatable:
            if field in updates:
                old = task.get(field)
                task[field] = updates[field]
                if old != updates[field]:
                    changed.append(field)

        if not changed:
            print(f"No changes to task {updates['id']}.")
            return

        # Re-validate DAG if dependencies changed
        if "depends_on" in updates:
            dag_errors = validate_dag(tracker["tasks"])
            if dag_errors:
                print(f"ERROR: Updated dependencies create invalid graph:", file=sys.stderr)
                for e in dag_errors:
                    print(f"  {e}", file=sys.stderr)
                sys.exit(1)

        save_tracker(args.project, tracker)
    print(f"Updated task {updates['id']}: {', '.join(changed)}")
    print_task_detail(task)


def cmd_remove_task(args):
    """Remove a TODO task from the graph."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)

    if task["status"] != "TODO":
        print(f"ERROR: Can only remove TODO tasks. {args.task_id} is {task['status']}.",
              file=sys.stderr)
        sys.exit(1)

    # Check if other tasks depend on this one
    dependents = [t["id"] for t in tracker["tasks"]
                  if args.task_id in t.get("depends_on", [])]
    if dependents:
        print(f"ERROR: Cannot remove {args.task_id} — these tasks depend on it: "
              f"{', '.join(dependents)}", file=sys.stderr)
        print(f"Update their depends_on first, or remove them.", file=sys.stderr)
        sys.exit(1)

    tracker["tasks"] = [t for t in tracker["tasks"] if t["id"] != args.task_id]
    save_tracker(args.project, tracker)
    print(f"Removed task {args.task_id} ({task['name']})")
    print_task_list(tracker)


# -- Subtask Commands --

def _next_subtask(project: str, tracker: dict, task: dict):
    """Find and return next subtask within a task."""
    subtasks = task.get("subtasks", [])

    # Check for IN_PROGRESS subtask (resume)
    for st in subtasks:
        if st["status"] == "IN_PROGRESS":
            idx = subtasks.index(st) + 1
            total = len(subtasks)
            print(f"## Current subtask: {st['id']} [{idx}/{total}]")
            print()
            print(f"**Parent**: {task['id']} — {task['name']}")
            print(f"Status: **IN_PROGRESS** (started: {st.get('started_at', '?')})")
            if st.get("description"):
                print(f"Description: {st['description']}")
            return

    # Find next TODO subtask
    for st in subtasks:
        if st["status"] == "TODO":
            st["status"] = "IN_PROGRESS"
            st["started_at"] = now_iso()
            task["subtask_done"] = sum(1 for s in subtasks if s["status"] == "DONE")
            save_tracker(project, tracker)

            idx = subtasks.index(st) + 1
            total = len(subtasks)

            print(f"## Next subtask: {st['id']} [{idx}/{total}]")
            print()
            print(f"**Parent**: {task['id']} — {task['name']}")
            print(f"Status: TODO -> **IN_PROGRESS**")
            if st.get("description"):
                print(f"Description: {st['description']}")
            return

    # All subtasks done
    done_count = sum(1 for s in subtasks if s["status"] == "DONE")
    print(f"## All subtasks complete: {task['id']} [{done_count}/{len(subtasks)}]")
    print()
    print(f"All {len(subtasks)} subtasks are DONE.")
    print()
    print(f"Complete the parent task:")
    print(f"  python -m core.pipeline complete {project} {task['id']}")


def cmd_register_subtasks(args):
    """Register subtasks for an IN_PROGRESS task."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)

    if task["status"] != "IN_PROGRESS":
        print(f"ERROR: Task {args.task_id} must be IN_PROGRESS to register subtasks (is {task['status']}).", file=sys.stderr)
        sys.exit(1)

    if task.get("has_subtasks"):
        print(f"WARNING: Task {args.task_id} already has {task.get('subtask_total', 0)} subtasks.")
        return

    try:
        raw = load_json_data(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["register-subtasks"], raw)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    subtask_entries = []
    for item in raw:
        subtask_entries.append({
            "id": f"{args.task_id}/{item['id']}",
            "name": item.get("name", item["id"]),
            "description": item.get("description", ""),
            "status": "TODO",
            "started_at": None,
            "completed_at": None,
        })

    task["has_subtasks"] = True
    task["subtask_total"] = len(subtask_entries)
    task["subtask_done"] = 0
    task["subtasks"] = subtask_entries

    save_tracker(args.project, tracker)

    print(f"## Subtasks registered: {args.task_id}")
    print(f"Total: {len(subtask_entries)}")
    print(f"\nRun `next {args.project}` to start.")


def cmd_complete_subtask(args):
    """Mark a subtask as DONE."""
    tracker = load_tracker(args.project)

    subtask_id = args.subtask_id
    if "/" not in subtask_id:
        print(f"ERROR: Invalid subtask ID '{subtask_id}'. Expected: TASK_ID/SUB_ID", file=sys.stderr)
        sys.exit(1)

    parent_id = subtask_id.rsplit("/", 1)[0]
    task = find_task(tracker, parent_id)

    if not task.get("has_subtasks"):
        print(f"ERROR: Task {parent_id} has no subtasks.", file=sys.stderr)
        sys.exit(1)

    subtask = None
    for st in task.get("subtasks", []):
        if st["id"] == subtask_id:
            subtask = st
            break

    if subtask is None:
        print(f"ERROR: Subtask '{subtask_id}' not found.", file=sys.stderr)
        sys.exit(1)

    if subtask["status"] == "DONE":
        print(f"WARNING: Subtask {subtask_id} already DONE.")
        return

    subtask["status"] = "DONE"
    subtask["completed_at"] = now_iso()

    done_count = sum(1 for s in task["subtasks"] if s["status"] == "DONE")
    task["subtask_done"] = done_count
    total = task["subtask_total"]

    save_tracker(args.project, tracker)

    print(f"Subtask {subtask_id}: DONE [{done_count}/{total}]")

    if done_count == total:
        print(f"\nAll {total} subtasks complete!")
        print(f"Complete parent: python -m core.pipeline complete {args.project} {parent_id}")


# -- Formatting --

STATUS_ICONS = {
    "TODO": "[ ]",
    "CLAIMING": "[?]",
    "IN_PROGRESS": "[>]",
    "DONE": "[x]",
    "SKIPPED": "[-]",
    "FAILED": "[!]",
}


def print_status(project: str, tracker: dict):
    """Print compact status dashboard."""
    tasks = tracker["tasks"]
    total = len(tasks)
    if total == 0:
        print(f"## {project} -- No tasks yet")
        print(f"Goal: {tracker.get('goal', '(none)')}")
        return

    done = sum(1 for t in tasks if t["status"] == "DONE")
    skipped = sum(1 for t in tasks if t["status"] == "SKIPPED")
    in_progress = [t for t in tasks if t["status"] == "IN_PROGRESS"]
    failed = [t for t in tasks if t["status"] == "FAILED"]
    todo = sum(1 for t in tasks if t["status"] == "TODO")

    print(f"## {project} -- Pipeline Status")
    print(f"Goal: {tracker.get('goal', '(none)')}")
    print(f"")
    parts = [f"Done: {done}/{total}", f"TODO: {todo}"]
    if skipped:
        parts.append(f"Skipped: {skipped}")
    if failed:
        parts.append(f"Failed: {len(failed)}")
    if in_progress:
        parts.append(f"Current: {in_progress[0]['id']}")
    print(f"  {' | '.join(parts)}")

    # Type breakdown (only if any non-default types exist)
    type_counts = {}
    for t in tasks:
        ttype = t.get("type", "feature")
        type_counts[ttype] = type_counts.get(ttype, 0) + 1
    if len(type_counts) > 1 or "feature" not in type_counts:
        type_parts = [f"{k}: {v}" for k, v in sorted(type_counts.items())]
        print(f"  Types: {' | '.join(type_parts)}")
    print(f"")

    # Progress bar
    filled = done + skipped
    bar_len = 20
    filled_chars = int(filled / total * bar_len) if total else 0
    bar = "#" * filled_chars + "." * (bar_len - filled_chars)
    print(f"  [{bar}] {filled}/{total}")
    print(f"")

    for task in tasks:
        icon = STATUS_ICONS.get(task["status"], "?")
        ttype = task.get("type", "feature")
        type_label = f" [{ttype}]" if ttype != "feature" else ""
        line = f"  {icon} {task['id']} {task['name']}{type_label}"
        agent_label = f" ({task['agent']})" if task.get("agent") else ""
        if task["status"] == "IN_PROGRESS":
            if task.get("has_subtasks"):
                line += f" <- current{agent_label} [{task.get('subtask_done', 0)}/{task.get('subtask_total', 0)} subtasks]"
            else:
                line += f" <- current{agent_label}"
        elif task["status"] == "CLAIMING":
            line += f" <- claiming{agent_label}"
        elif task["status"] == "FAILED":
            line += f" -- {task.get('failed_reason', '')}"
        print(line)

    # "Where was I?" — show resumption context for IN_PROGRESS or next TODO task
    active = in_progress[0] if in_progress else None
    if not active:
        # Find next TODO task (same logic as cmd_next)
        done_ids = {t["id"] for t in tasks if t["status"] in ("DONE", "SKIPPED")}
        for t in tasks:
            if t["status"] == "TODO":
                deps = set(t.get("depends_on", []))
                if deps.issubset(done_ids):
                    active = t
                    break

    if active:
        print()
        label = "Current task" if active["status"] == "IN_PROGRESS" else "Next task"
        print(f"  ### {label}: {active['id']} — {active['name']}")
        if active.get("description"):
            print(f"  {active['description'][:120]}")

        # Show acceptance criteria with change-based progress
        ac = active.get("acceptance_criteria", [])
        if ac:
            # Load changes to check what's recorded for this task
            _s = _get_storage()
            ch_data = _s.load_data(project, 'changes')
            recorded_files = {
                c.get("summary", "").lower()
                for c in ch_data.get("changes", [])
                if c.get("task_id") == active["id"]
            }

            print(f"  Acceptance criteria ({len(ac)}):")
            for criterion in ac:
                if isinstance(criterion, dict):
                    text = criterion.get("text", "")
                    tmpl = criterion.get("from_template")
                    if tmpl:
                        print(f"    - {text} (from {tmpl})")
                    else:
                        print(f"    - {text}")
                else:
                    print(f"    - {criterion}")

        # Show recorded changes count
        _s = _get_storage()
        ch_data = _s.load_data(project, 'changes')
        task_changes = [c for c in ch_data.get("changes", [])
                       if c.get("task_id") == active["id"]]
        if task_changes:
            print(f"  Changes recorded: {len(task_changes)} files")

    # DAG visualization
    print()
    print_dag(tasks)


def print_dag(tasks: list):
    """Print ASCII dependency graph."""
    if not tasks:
        return

    task_map = {t["id"]: t for t in tasks}
    # Find root tasks (no dependencies)
    roots = [t["id"] for t in tasks if not t.get("depends_on")]
    # Find children for each task
    children = {}
    for t in tasks:
        for dep in t.get("depends_on", []):
            children.setdefault(dep, []).append(t["id"])

    if not roots and tasks:
        # All tasks have deps — show flat
        roots = [tasks[0]["id"]]

    printed = set()

    def _render(tid, prefix="", is_last=True):
        if tid in printed:
            return
        printed.add(tid)
        t = task_map.get(tid)
        if not t:
            return
        icon = STATUS_ICONS.get(t["status"], "?")
        connector = "└── " if is_last else "├── "
        print(f"  {prefix}{connector}{icon} {tid} {t['name']}")
        kids = children.get(tid, [])
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, kid in enumerate(kids):
            _render(kid, child_prefix, i == len(kids) - 1)

    print("```")
    print(f"  {task_map.get(roots[0], {}).get('name', 'project') if roots else 'project'}")
    for i, root in enumerate(roots):
        _render(root, "", i == len(roots) - 1)
    # Show orphans (tasks not reached from roots)
    for t in tasks:
        if t["id"] not in printed:
            _render(t["id"], "", True)
    print("```")


def print_task_list(tracker: dict):
    """Print all tasks as MD table."""
    print("| # | ID | Name | Type | Status | Depends On | Blocked By |")
    print("|---|-----|------|------|--------|------------|------------|")
    for i, task in enumerate(tracker["tasks"], 1):
        deps = ", ".join(task["depends_on"]) if task["depends_on"] else "--"
        ttype = task.get("type", "feature")
        blocked = ", ".join(task.get("blocked_by_decisions", [])) or "--"
        icon = STATUS_ICONS.get(task["status"], "?")
        print(f"| {i} | {task['id']} | {task['name']} | {ttype} | {icon} {task['status']} | {deps} | {blocked} |")


def print_task_detail(task: dict):
    """Print full task detail."""
    ttype = task.get("type", "feature")
    if ttype != "feature":
        print(f"**Type**: {ttype}")

    if task.get("description"):
        print(f"**Description**: {task['description']}")
        print(f"")

    if task.get("skill"):
        print(f"**Skill**: `{task['skill']}`")
        print(f"Action: Read the SKILL file and follow its procedure.")
    elif task.get("instruction"):
        print(f"**Instruction**: {task['instruction']}")

    print(f"")
    if task["depends_on"]:
        print(f"**Dependencies**: {', '.join(task['depends_on'])}")

    blocked = task.get("blocked_by_decisions", [])
    if blocked:
        print(f"**Blocked by decisions**: {', '.join(blocked)}")

    k_ids = task.get("knowledge_ids", [])
    if k_ids:
        print(f"**Knowledge**: {', '.join(k_ids)}")

    alignment = task.get("alignment")
    if alignment:
        print(f"")
        print(f"**Alignment Contract**:")
        if alignment.get("goal"):
            print(f"  Goal: {alignment['goal']}")
        bounds = alignment.get("boundaries", {})
        if bounds.get("must"):
            for m in bounds["must"]:
                print(f"  Must: {m}")
        if bounds.get("must_not"):
            for m in bounds["must_not"]:
                print(f"  Must not: {m}")
        if alignment.get("success"):
            print(f"  Success: {alignment['success']}")

    test_req = task.get("test_requirements")
    if test_req:
        parts = []
        if test_req.get("unit"):
            parts.append("unit")
        if test_req.get("integration"):
            parts.append("integration")
        if test_req.get("e2e"):
            parts.append("e2e")
        label = ", ".join(parts) if parts else "none specified"
        print(f"**Test Requirements**: {label}")
        if test_req.get("description"):
            print(f"  {test_req['description']}")

    ac = task.get("acceptance_criteria", [])
    if ac:
        print(f"")
        print(f"**Acceptance Criteria**:")
        has_mechanical = False
        has_manual = False
        for criterion in ac:
            if isinstance(criterion, dict):
                text = criterion.get("text", "")
                verification = criterion.get("verification", "manual")
                tmpl = criterion.get("from_template")
                if verification in ("test", "command"):
                    has_mechanical = True
                    cmd = criterion.get("command") or criterion.get("test_path") or ""
                    if tmpl:
                        print(f"  - [ ] {text} (from {tmpl}) [{verification}: `{cmd}`]")
                    else:
                        print(f"  - [ ] {text} [{verification}: `{cmd}`]")
                else:
                    has_manual = True
                    if tmpl:
                        print(f"  - [ ] {text} (from {tmpl})")
                    else:
                        print(f"  - [ ] {text}")
            else:
                has_manual = True
                print(f"  - [ ] {criterion}")

        # AC verification instructions for LLM
        print(f"")
        print(f"**AC Verification Requirements**:")
        if has_mechanical:
            print(f"  Mechanical AC (test/command) will be executed automatically at completion.")
            print(f"  These BLOCK completion if they fail — regardless of task type or ceremony level.")
        if has_manual:
            print(f"  Manual AC requires --ac-reasoning with CONCRETE EVIDENCE for each criterion.")
            print(f"  Rules:")
            print(f"    - Minimum 50 characters total")
            print(f"    - Each AC must be addressed: 'AC N: [criterion text] — PASS: [evidence]'")
            print(f"    - Evidence must be specific: file path, command output, test result, or observable fact")
            print(f"    - 'Done', 'verified', 'works as expected' are NOT acceptable evidence")
            print(f"    - If you ran a command to verify, include the command and its output")
            print(f"    - If you read code to verify, cite the file and line numbers")

    excl = task.get("exclusions", [])
    if excl:
        print(f"")
        print(f"**Exclusions (DO NOT)**:")
        for ex in excl:
            print(f"  - {ex}")

    produces = task.get("produces")
    if produces:
        print(f"")
        print(f"**Produces (contract for downstream tasks)**:")
        for key, val in produces.items():
            print(f"  {key}: {val}")

    print(f"")
    print(f"When done: `python -m core.pipeline complete {{project}} {task['id']}`")


# -- Context & Config Commands --

def _objective_kr_pct(baseline, target, current) -> int:
    """Calculate KR progress percentage (0-100)."""
    try:
        baseline, target, current = float(baseline), float(target), float(current)
    except (TypeError, ValueError):
        return 0
    total_delta = target - baseline
    if total_delta == 0:
        return 100 if current == target else 0
    return max(0, min(100, int((current - baseline) / total_delta * 100)))


def _estimate_context_size(project: str, task_ids: set) -> int:
    """Estimate context size in characters for the given dependency tasks."""
    total = 0
    _s = _get_storage()
    for entity in ("changes", "decisions", "lessons"):
        if _s.exists(project, entity):
            data = _s.load_data(project, entity)
            for entry in data.get(entity, []):
                if entry.get("task_id") in task_ids:
                    total += len(json.dumps(entry))
    return total


def _check_plan_staleness(task, tracker):
    """Check if files mentioned in task instruction were modified since plan approval.

    Uses git log to detect external changes. Returns list of warning strings.
    """
    import subprocess as _sp

    approved_at = tracker.get("plan_approved_at")
    if not approved_at:
        return []

    instruction = (task.get("instruction") or "") + " " + (task.get("description") or "")
    if not instruction.strip():
        return []

    # Extract file paths from instruction (patterns: backtick paths, quoted paths, common extensions)
    path_patterns = re.findall(
        r'`([^`]+\.[a-zA-Z]{1,5})`'           # `path/to/file.ext`
        r'|(?:^|\s)([\w/\-\.]+\.[a-zA-Z]{1,5})'  # bare path/to/file.ext
        r'|(?:^|\s)([\w/\-]+/[\w/\-]+)',            # directory/paths
        instruction
    )
    # Flatten and deduplicate
    candidates = set()
    for groups in path_patterns:
        for g in groups:
            if g and len(g) > 3 and '/' in g:
                candidates.add(g.strip())

    if not candidates:
        return []

    warnings = []
    for filepath in sorted(candidates):
        try:
            result = _sp.run(
                f'git log --oneline --since="{approved_at}" -- "{filepath}"',
                shell=True, capture_output=True, text=True,
                encoding="utf-8", timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split("\n")
                warnings.append(
                    f"`{filepath}` modified since plan approval ({len(commits)} commit(s)): "
                    f"{commits[0][:60]}"
                )
        except Exception:
            pass

    return warnings


def _check_contract_alignment(task, tracker):
    """Check if task instruction references key terms from dependency produces contracts.

    Returns list of warning strings (empty if all aligned).
    """
    warnings = []
    instruction = ((task.get("instruction") or "") + " " + (task.get("description") or "")).lower()
    if not instruction.strip():
        return warnings

    stop_words = {"http", "https", "with", "from", "that", "this", "will", "must",
                  "should", "into", "when", "then", "each", "also", "used", "none"}

    for dep_id in task.get("depends_on", []):
        dep_task = None
        for t in tracker["tasks"]:
            if t["id"] == dep_id:
                dep_task = t
                break
        if not dep_task or not dep_task.get("produces"):
            continue

        for key, val in dep_task["produces"].items():
            val_str = str(val).lower()
            terms = re.split(r'[\s/\->{},():\[\]]+', val_str)
            terms = [t for t in terms if len(t) > 3 and t not in stop_words]

            if terms and not any(term in instruction for term in terms):
                warnings.append(
                    f"Dependency {dep_id} produces `{key}: {val}` "
                    f"but task instruction does not reference it. Verify alignment."
                )

    return warnings


def cmd_context(args):
    """Show aggregated context for a task: dependency outputs, decisions, changes."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)
    lean = getattr(args, "lean", False)

    print(f"## Context for {args.task_id}: {task['name']}")
    if lean:
        print("*(lean mode — Knowledge, Research, Business Context, Lessons skipped)*")
    print()

    # Pre-load decisions (used in multiple sections below)
    _s = _get_storage()
    dec_data = _s.load_data(args.project, 'decisions')

    # Task details
    if task.get("description"):
        print(f"**Description**: {task['description']}")
    if task.get("instruction"):
        print(f"**Instruction**: {task['instruction']}")
    print()

    # Alignment contract (persisted from planning)
    alignment = task.get("alignment")
    if alignment:
        print("### Alignment Contract")
        print()
        if alignment.get("goal"):
            print(f"**Goal**: {alignment['goal']}")
        bounds = alignment.get("boundaries", {})
        if bounds.get("must"):
            print("**Must**:")
            for m in bounds["must"]:
                print(f"  - {m}")
        if bounds.get("must_not"):
            print("**Must not**:")
            for m in bounds["must_not"]:
                print(f"  - {m}")
        if bounds.get("not_in_scope"):
            print("**Not in scope**:")
            for m in bounds["not_in_scope"]:
                print(f"  - {m}")
        if alignment.get("success"):
            print(f"**Success criteria**: {alignment['success']}")
        print()

    # Exclusions (task-specific DO NOT rules)
    excl = task.get("exclusions", [])
    if excl:
        print("### Exclusions")
        print()
        for ex in excl:
            print(f"- **DO NOT**: {ex}")
        print()

    # Plan staleness check: were files modified since plan approval?
    staleness_warnings = _check_plan_staleness(task, tracker)
    if staleness_warnings:
        print("### Plan Staleness Warnings")
        print()
        print("These files were modified **after** the plan was approved. Your task instruction may be outdated:")
        print()
        for w in staleness_warnings:
            print(f"- {w}")
        print()
        print("**Action**: Read the modified files before starting. If changes conflict with your instruction, create an OPEN decision.")
        print()

    # Dependency context
    deps = task.get("depends_on", [])
    if deps:
        print(f"### Completed Dependencies")
        print()
        for dep_id in deps:
            dep_task = find_task(tracker, dep_id)
            print(f"**{dep_id}** — {dep_task['name']} ({dep_task['status']})")
            if dep_task.get("description"):
                print(f"  {dep_task['description']}")
            dep_produces = dep_task.get("produces")
            if dep_produces:
                print(f"  **Produces**:")
                for key, val in dep_produces.items():
                    print(f"    {key}: {val}")
            print()

        # Contract alignment check
        contract_warnings = _check_contract_alignment(task, tracker)
        if contract_warnings:
            print("### Contract Alignment Warnings")
            print()
            for w in contract_warnings:
                print(f"- {w}")
            print()

        # Show changes from dependency tasks
        changes_data = _s.load_data(args.project, 'changes')
        dep_changes = [c for c in changes_data.get("changes", [])
                       if c.get("task_id") in deps]
        if dep_changes:
            print(f"### Changes from Dependencies")
            print()
            print("| Task | File | Action | Summary |")
            print("|------|------|--------|---------|")
            for c in dep_changes:
                summary = c.get("summary", "")[:50]
                print(f"| {c['task_id']} | {c['file']} | {c['action']} | {summary} |")
            print()
            # Prominent instruction to read dependency files
            dep_files = sorted({c["file"] for c in dep_changes if c.get("file")})
            if dep_files:
                print("**READ THESE FILES before starting** (modified by dependencies):")
                for f in dep_files:
                    print(f"  - `{f}`")
                print()

        # Show decisions from dependency tasks
        if dec_data:
            dep_decisions = [d for d in dec_data.get("decisions", [])
                             if d.get("task_id") in deps]
            if dep_decisions:
                print(f"### Decisions from Dependencies")
                print()
                for d in dep_decisions:
                    status = d.get("status", "")
                    print(f"- **{d['id']}** ({status}): {d.get('issue', '')}")
                    if d.get("recommendation"):
                        print(f"  Recommendation: {d['recommendation']}")
                print()
    else:
        print("No dependencies — this is a root task.")
        print()

    # Show open decisions for this task
    if dec_data:
        task_decisions = [d for d in dec_data.get("decisions", [])
                          if d.get("task_id") == args.task_id]
        if task_decisions:
            print(f"### Existing Decisions for This Task")
            print()
            for d in task_decisions:
                print(f"- **{d['id']}** ({d.get('status', '')}): {d.get('issue', '')}")
            print()

        # Show decisions that AFFECT this task (from other tasks' --deferred)
        affecting = [d for d in dec_data.get("decisions", [])
                     if args.task_id in (d.get("affects") or [])
                     and d.get("task_id") != args.task_id]
        if affecting:
            print(f"### Decisions Affecting This Task")
            print()
            for d in affecting:
                print(f"- **{d['id']}** ({d.get('status', '')}): {d.get('issue', '')}")
                if d.get("recommendation"):
                    print(f"  → {d['recommendation']}")
            print()

    # Show relevant lessons (skip in lean mode)
    if not lean:
        lessons_data = _s.load_data(args.project, 'lessons')
        lessons = lessons_data.get("lessons", [])
        if lessons:
            print(f"### Relevant Lessons")
            print()
            for l in lessons:
                print(f"- **{l['id']}** [{l.get('severity', '')}]: {l['title']}")
            print()

    # Compute task_scopes (shared by guidelines and knowledge scope matching)
    g_data = _s.load_data(args.project, 'guidelines')
    project_guidelines = [g for g in g_data.get("guidelines", []) if g.get("status") == "ACTIVE"]

    task_scopes = set(task.get("scopes", []))
    origin_for_scopes = task.get("origin", "")
    if origin_for_scopes.startswith("O-") and _s.exists(args.project, 'objectives'):
        obj_data_scopes = _s.load_data(args.project, 'objectives')
        for obj in obj_data_scopes.get("objectives", []):
            if obj["id"] == origin_for_scopes:
                task_scopes.update(obj.get("scopes", []))
                derived_gl_ids = set(obj.get("derived_guidelines", []))
                if derived_gl_ids:
                    for g in project_guidelines:
                        if g["id"] in derived_gl_ids and g.get("scope"):
                            task_scopes.add(g["scope"])
                break
    elif origin_for_scopes.startswith("I-") and _s.exists(args.project, 'ideas'):
        ideas_data_sc = _s.load_data(args.project, 'ideas')
        for idea in ideas_data_sc.get("ideas", []):
            if idea["id"] == origin_for_scopes:
                task_scopes.update(idea.get("scopes", []))
                obj_ids_sc = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                if obj_ids_sc and _s.exists(args.project, 'objectives'):
                    obj_data_sc = _s.load_data(args.project, 'objectives')
                    for obj in obj_data_sc.get("objectives", []):
                        if obj["id"] in obj_ids_sc:
                            derived_gl_ids = set(obj.get("derived_guidelines", []))
                            for g in project_guidelines:
                                if g["id"] in derived_gl_ids and g.get("scope"):
                                    task_scopes.add(g["scope"])
                break
    task_scopes.add("general")

    # Guidelines context (uses shared renderer from guidelines module)
    global_guidelines = []
    if args.project != "_global":
        g_global = _s.load_global('guidelines')
        global_guidelines = [g for g in g_global.get("guidelines", []) if g.get("status") == "ACTIVE"]

    # In lean mode, only show must-weight guidelines
    if lean:
        project_guidelines = [g for g in project_guidelines if g.get("weight") == "must"]
        global_guidelines = [g for g in global_guidelines if g.get("weight") == "must"]

    if global_guidelines or project_guidelines:
        from guidelines import render_guidelines_context
        lines = render_guidelines_context(project_guidelines, task_scopes, args.project,
                                           global_guidelines=global_guidelines)
        for line in lines:
            print(line)

    # Knowledge context (from task.knowledge_ids + origin chain + scope matching)
    k_ids = set(task.get("knowledge_ids", []))
    origin_k = task.get("origin", "")
    if origin_k.startswith("I-"):
        if _s.exists(args.project, 'ideas'):
            ideas_data = _s.load_data(args.project, 'ideas')
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == origin_k:
                    k_ids.update(idea.get("knowledge_ids", []))
                    obj_ids_k = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                    if obj_ids_k and _s.exists(args.project, 'objectives'):
                        obj_data_k = _s.load_data(args.project, 'objectives')
                        for obj in obj_data_k.get("objectives", []):
                            if obj["id"] in obj_ids_k:
                                k_ids.update(obj.get("knowledge_ids", []))
                    break
    elif origin_k.startswith("O-"):
        if _s.exists(args.project, 'objectives'):
            obj_data_k = _s.load_data(args.project, 'objectives')
            for obj in obj_data_k.get("objectives", []):
                if obj["id"] == origin_k:
                    k_ids.update(obj.get("knowledge_ids", []))
                    break

    # Load knowledge data once (used for both explicit and scope matching; skip in lean mode)
    k_data = {}
    if not lean and _s.exists(args.project, 'knowledge'):
        k_data = _s.load_data(args.project, 'knowledge')

    # Scope-matched knowledge (additive to explicit IDs)
    scope_matched_k_ids = set()
    if task_scopes and k_data:
        for k_obj in k_data.get("knowledge", []):
            if k_obj.get("status") != "ACTIVE":
                continue
            k_scopes = set(k_obj.get("scopes", []))
            if k_scopes & task_scopes and k_obj["id"] not in k_ids:
                scope_matched_k_ids.add(k_obj["id"])

    all_k_ids = k_ids | scope_matched_k_ids
    if all_k_ids and k_data:
        k_objects = {k["id"]: k for k in k_data.get("knowledge", [])
                     if k.get("status") == "ACTIVE"}

        explicit_linked = [k_objects[kid] for kid in sorted(k_ids) if kid in k_objects]
        scope_linked = [k_objects[kid] for kid in sorted(scope_matched_k_ids) if kid in k_objects]

        # Cap scope-matched at 10 to prevent context bloat
        if len(scope_linked) > 10:
            scope_linked = scope_linked[:10]

        total = len(explicit_linked) + len(scope_linked)
        if total > 0:
            print(f"### Knowledge ({total})")
            print()
            for k in explicit_linked:
                print(f"**{k['id']}**: {k['title']} [{k['category']}]")
                content_preview = k.get("content", "")[:200]
                if content_preview:
                    print(f"  {content_preview}")
            if scope_linked:
                print()
                print(f"*Scope-matched ({len(scope_linked)}):*")
                for k in scope_linked:
                    print(f"**{k['id']}**: {k['title']} [{k['category']}]")
                    content_preview = k.get("content", "")[:200]
                    if content_preview:
                        print(f"  {content_preview}")
            print()

    # Research context (from task origin -> idea/objective -> research; skip in lean mode)
    if not lean and _s.exists(args.project, 'research'):
        r_data = _s.load_data(args.project, 'research')
        active_research = [r for r in r_data.get("research", [])
                          if r.get("status") == "ACTIVE"]
        task_research = []
        origin = task.get("origin", "")

        if origin.startswith("I-"):
            # Research linked to origin idea
            task_research = [r for r in active_research
                            if r.get("linked_entity_id") == origin
                            or r.get("linked_idea_id") == origin]
            # Also research linked to objective (via idea.advances_key_results)
            if _s.exists(args.project, 'ideas'):
                ideas_data_r = _s.load_data(args.project, 'ideas')
                for idea in ideas_data_r.get("ideas", []):
                    if idea["id"] == origin:
                        obj_ids_r = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                        task_research.extend([r for r in active_research
                                             if r.get("linked_entity_id") in obj_ids_r
                                             and r["id"] not in {x["id"] for x in task_research}])
                        break
        elif origin.startswith("O-"):
            # Direct objective origin (from /plan O-001)
            task_research = [r for r in active_research
                            if r.get("linked_entity_id") == origin]

        if task_research:
            seen = set()
            unique = [r for r in task_research if r["id"] not in seen and not seen.add(r["id"])]
            print(f"### Research ({len(unique)})")
            print()
            for r in sorted(unique, key=lambda x: x["id"]):
                print(f"**{r['id']}**: {r['title']} [{r['category']}]")
                if r.get("summary"):
                    print(f"  {r['summary'][:200]}")
                for f in (r.get("key_findings") or [])[:5]:
                    print(f"  - {f}")
                if r.get("decision_ids"):
                    print(f"  Related decisions: {', '.join(r['decision_ids'])}")
            print()

    # Test requirements
    test_req = task.get("test_requirements")
    if test_req:
        print(f"### Test Requirements")
        print()
        parts = []
        if test_req.get("unit"):
            parts.append("unit")
        if test_req.get("integration"):
            parts.append("integration")
        if test_req.get("e2e"):
            parts.append("e2e")
        if parts:
            print(f"Required: {', '.join(parts)}")
        if test_req.get("description"):
            print(f"{test_req['description']}")
        print()

    # Business context: trace task → origin → objective (skip in lean mode)
    origin = task.get("origin", "")
    if not lean and origin.startswith("O-"):
        # Direct objective origin (from /plan O-001)
        if _s.exists(args.project, 'objectives'):
            obj_data = _s.load_data(args.project, 'objectives')
            for obj in obj_data.get("objectives", []):
                if obj["id"] == origin:
                    print("### Business Context")
                    print()
                    print(f"**{obj['id']}**: {obj['title']} [{obj['status']}]")
                    for kr in obj.get("key_results", []):
                        target = kr.get("target")
                        if target is not None:
                            baseline = kr.get("baseline", 0)
                            current = kr.get("current", baseline)
                            pct = _objective_kr_pct(baseline, target, current)
                            print(f"  {kr['id']}: {kr.get('metric', '')} — {current}/{target} ({pct}%)")
                        else:
                            desc = kr.get("description") or kr.get("metric", "")
                            status = kr.get("status", "")
                            print(f"  {kr['id']}: {desc} [{status}]")
                    print(f"  Origin: objective {origin}")
                    print()
                    break
    elif not lean and origin.startswith("I-"):
        if _s.exists(args.project, 'ideas') and _s.exists(args.project, 'objectives'):
            ideas_data = _s.load_data(args.project, 'ideas')
            obj_data = _s.load_data(args.project, 'objectives')
            # Find origin idea
            origin_idea = None
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == task["origin"]:
                    origin_idea = idea
                    break
            if origin_idea and origin_idea.get("advances_key_results"):
                # Find linked objectives
                obj_ids = {kr_ref.split("/")[0] for kr_ref in origin_idea["advances_key_results"]
                           if "/" in kr_ref}
                linked_objs = [o for o in obj_data.get("objectives", []) if o["id"] in obj_ids]
                if linked_objs:
                    print("### Business Context")
                    print()
                    for obj in linked_objs:
                        print(f"**{obj['id']}**: {obj['title']} [{obj['status']}]")
                        # Show only relevant KRs
                        relevant_kr_ids = {kr_ref.split("/")[1] for kr_ref in origin_idea["advances_key_results"]
                                           if kr_ref.startswith(obj["id"] + "/")}
                        for kr in obj.get("key_results", []):
                            if kr["id"] in relevant_kr_ids:
                                target = kr.get("target")
                                if target is not None:
                                    baseline = kr.get("baseline", 0)
                                    current = kr.get("current", baseline)
                                    pct = _objective_kr_pct(baseline, target, current)
                                    print(f"  {kr['id']}: {kr.get('metric', '')} — {current}/{target} ({pct}%)")
                                else:
                                    desc = kr.get("description") or kr.get("metric", "")
                                    status = kr.get("status", "")
                                    print(f"  {kr['id']}: {desc} [{status}]")
                    print(f"  Via idea: {origin_idea['id']} \"{origin_idea['title']}\"")
                    print()

    # Risks (type=risk decisions) linked to this task or origin idea
    if _s.exists(args.project, 'decisions'):
        risk_decisions = [d for d in dec_data.get("decisions", [])
                          if d.get("type") == "risk"
                          and d.get("status") not in ("CLOSED",)]
        task_risks = [d for d in risk_decisions
                      if d.get("linked_entity_type") == "task"
                      and d.get("linked_entity_id") == args.task_id]
        # Also show risks from origin idea
        if task.get("origin") and task["origin"].startswith("I-"):
            idea_risks = [d for d in risk_decisions
                          if d.get("linked_entity_type") == "idea"
                          and d.get("linked_entity_id") == task["origin"]]
            task_risks.extend(idea_risks)
        # Also show risks from origin objective
        if task.get("origin") and task["origin"].startswith("O-"):
            obj_risks = [d for d in risk_decisions
                         if d.get("linked_entity_type") == "objective"
                         and d.get("linked_entity_id") == task["origin"]]
            task_risks.extend(obj_risks)
        if task_risks:
            print(f"### Active Risks ({len(task_risks)})")
            print()
            for r in task_risks:
                print(f"- **{r['id']}** [{r.get('severity', '')}/{r.get('likelihood', '')}] "
                      f"({r.get('status', '')}): {r.get('issue', '')}")
                if r.get("mitigation_plan"):
                    print(f"  Mitigation: {r['mitigation_plan'][:80]}")
            print()

    # Context budget estimate
    all_task_ids = set(deps) | {args.task_id}
    ctx_chars = _estimate_context_size(args.project, all_task_ids)
    ctx_kb = ctx_chars / 1024
    print(f"### Context Budget")
    print(f"Estimated context from dependencies: {ctx_kb:.1f} KB ({ctx_chars} chars)")
    if ctx_kb > 50:
        print(f"**WARNING**: Large context. Consider summarizing older dependency outputs.")
    print()


def cmd_config(args):
    """Set or show project configuration."""
    tracker = load_tracker(args.project)

    if args.data:
        try:
            config = load_json_data(args.data)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

        if not isinstance(config, dict):
            print("ERROR: --data must be a JSON object", file=sys.stderr)
            sys.exit(1)

        known_keys = set(CONTRACTS["config"]["optional"])
        unknown = set(config.keys()) - known_keys
        if unknown:
            print(f"WARNING: Unknown config keys: {', '.join(sorted(unknown))}", file=sys.stderr)

        existing = tracker.get("config", {})
        existing.update(config)
        tracker["config"] = existing
        save_tracker(args.project, tracker)

        print(f"Config updated for '{args.project}':")
        for k, v in existing.items():
            print(f"  {k}: {v}")
    else:
        config = tracker.get("config", {})
        if not config:
            print(f"No config set for '{args.project}'.")
            print()
            print("Set with:")
            print(f'  python -m core.pipeline config {args.project} --data \'{{"test_cmd": "pytest", "lint_cmd": "ruff check .", "branch_prefix": "forge/"}}\'')
            return
        print(f"## Config: {args.project}")
        print()
        for k, v in config.items():
            print(f"  {k}: {v}")


# -- Plan Validation --


def _validate_plan_references(entries: list, project: str) -> list:
    """Validate origin, scopes, knowledge_ids references. Returns list of warning strings."""
    warnings = []
    _s = _get_storage()

    # Collect valid IDs for batch checking
    valid_idea_ids = set()
    valid_obj_ids = set()
    valid_k_ids = set()
    valid_scopes = set()

    if _s.exists(project, 'ideas'):
        ideas = _s.load_data(project, 'ideas').get("ideas", [])
        valid_idea_ids = {i["id"] for i in ideas}
    if _s.exists(project, 'objectives'):
        objs = _s.load_data(project, 'objectives').get("objectives", [])
        valid_obj_ids = {o["id"] for o in objs}
    if _s.exists(project, 'knowledge'):
        k_data = _s.load_data(project, 'knowledge').get("knowledge", [])
        valid_k_ids = {k["id"] for k in k_data if k.get("status") == "ACTIVE"}
    if _s.exists(project, 'guidelines'):
        g_data = _s.load_data(project, 'guidelines').get("guidelines", [])
        valid_scopes = {g["scope"] for g in g_data if g.get("scope") and g.get("status") == "ACTIVE"}
        valid_scopes.add("general")

    for t in entries:
        tid = t.get("id", "?")

        # Origin validation
        origin = t.get("origin", "")
        if origin:
            if origin.startswith("I-") and origin not in valid_idea_ids:
                warnings.append(f"  {tid}: origin '{origin}' — idea not found")
            elif origin.startswith("O-") and origin not in valid_obj_ids:
                warnings.append(f"  {tid}: origin '{origin}' — objective not found")

        # Scope validation (only warn if guidelines exist for the project)
        for scope in t.get("scopes", []):
            if valid_scopes and scope != "general" and scope not in valid_scopes:
                warnings.append(f"  {tid}: scope '{scope}' — no guidelines with this scope")

        # Knowledge validation
        for kid in t.get("knowledge_ids", []):
            if kid not in valid_k_ids:
                warnings.append(f"  {tid}: knowledge '{kid}' — not found or not ACTIVE")

    return warnings


def _validate_ac_reasoning(ac_reasoning: str, ac_list: list) -> list:
    """Validate that AC reasoning addresses each criterion with evidence.

    Returns list of error strings. Empty = valid.
    Checks:
    - Each AC is addressed (by number or text fragment)
    - PASS/FAIL verdict is present
    - Reasoning is not just filler words
    """
    errors = []
    reasoning_lower = ac_reasoning.lower()

    # Reject filler-only reasoning
    filler_patterns = {"done", "verified", "works", "completed", "all good",
                       "looks good", "checked", "confirmed", "ok", "passed"}
    stripped_words = set(reasoning_lower.replace(".", "").replace(",", "").split())
    if stripped_words.issubset(filler_patterns | {"ac", "all", "the", "is", "are", "and", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-", ":", "—"}):
        errors.append("  AC reasoning contains only filler words. Provide concrete evidence.")

    # Filter to only manual AC for validation
    manual_ac = [c for c in ac_list if isinstance(c, str) or
                 (isinstance(c, dict) and c.get("verification", "manual") == "manual")]

    # Check that reasoning mentions each manual AC (by number or text fragment)
    for i, criterion in enumerate(manual_ac, 1):
        text = criterion if isinstance(criterion, str) else criterion.get("text", "")
        markers = [f"ac-{i}:", f"ac{i}:", f"ac {i}:", f"{i}.", f"{i}:"]
        text_fragment = text[:30].lower().strip()

        found = any(m in reasoning_lower for m in markers) or (
            len(text_fragment) > 10 and text_fragment in reasoning_lower
        )
        if not found:
            errors.append(f"  AC {i} not addressed: \"{text[:60]}\"")

    # Check for PASS/FAIL keywords
    if "pass" not in reasoning_lower and "met" not in reasoning_lower and "verified" not in reasoning_lower:
        errors.append("  No PASS/met/verified verdict found in reasoning")

    return errors


# -- AC Quality --

_VAGUE_AC_WORDS = {"handle", "handles", "ensure", "ensures", "properly", "robust",
                   "correctly", "works", "appropriate", "appropriately",
                   "should work", "as expected", "as needed"}


def _warn_ac_quality(tasks: list) -> bool:
    """Print warnings for missing or vague acceptance criteria.

    Returns True if there are BLOCKING issues (feature/bug without AC).
    """
    warnings = []
    errors = []
    for t in tasks:
        tid = t.get("id", "?")
        ttype = t.get("type", "feature")
        ac = t.get("acceptance_criteria", [])

        if ttype in ("investigation", "chore"):
            continue

        if not ac:
            errors.append(f"  {tid} ({t.get('name', '?')}): feature/bug task has no acceptance criteria")
            continue

        for criterion in ac:
            text = criterion if isinstance(criterion, str) else criterion.get("text", "")
            text_lower = text.lower()
            found = [w for w in _VAGUE_AC_WORDS if w in text_lower]
            if found:
                warnings.append(
                    f"  {tid}: vague AC \"{text[:60]}\" — contains: {', '.join(found)}"
                )

    if errors:
        print()
        print(f"**AC ERRORS** ({len(errors)}) — must fix before approving:")
        for e in errors:
            print(e)
        print("Add acceptance_criteria to feature/bug tasks, or set type to 'chore'/'investigation'.")
        print()

    if warnings:
        print()
        print(f"**AC QUALITY WARNINGS** ({len(warnings)}):")
        for w in warnings:
            print(w)
        print("Tip: rewrite vague AC as observable outcomes. "
              "E.g., 'handles errors' → 'returns 400 with {error} body for invalid input'")
        print()

    return len(errors) > 0


# -- CLI --

def _check_assumptions_readiness(assumptions_raw):
    """Parse and validate assumptions for readiness gate.

    Returns (parsed_assumptions, high_count).
    Exits on invalid JSON or schema.
    """
    try:
        assumptions = load_json_data(assumptions_raw)
    except (json.JSONDecodeError, Exception) as e:
        print(f"ERROR: Invalid assumptions JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(assumptions, list):
        print("ERROR: --assumptions must be a JSON array", file=sys.stderr)
        sys.exit(1)

    valid_severities = {"HIGH", "MED", "LOW"}
    for i, a in enumerate(assumptions):
        if not isinstance(a, dict):
            print(f"ERROR: Assumption {i+1} must be an object with assumption, basis, severity", file=sys.stderr)
            sys.exit(1)
        for field in ("assumption", "basis", "severity"):
            if field not in a:
                print(f"ERROR: Assumption {i+1} missing required field '{field}'", file=sys.stderr)
                sys.exit(1)
        if a["severity"] not in valid_severities:
            print(f"ERROR: Assumption {i+1} severity must be HIGH, MED, or LOW (got '{a['severity']}')", file=sys.stderr)
            sys.exit(1)

    high_count = sum(1 for a in assumptions if a["severity"] == "HIGH")
    return assumptions, high_count


def _check_coverage(coverage_raw):
    """Parse and validate coverage data. Blocks if any requirement has status MISSING.

    Each item: {requirement, source, covered_by, status, reason?}
    status: COVERED | DEFERRED | OUT_OF_SCOPE | MISSING
    DEFERRED and OUT_OF_SCOPE require reason field.

    Returns (parsed_coverage, missing_count, deferred_items).
    Exits on invalid JSON or schema.
    """
    try:
        coverage = load_json_data(coverage_raw)
    except (json.JSONDecodeError, Exception) as e:
        print(f"ERROR: Invalid coverage JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(coverage, list):
        print("ERROR: --coverage must be a JSON array", file=sys.stderr)
        sys.exit(1)

    valid_statuses = {"COVERED", "DEFERRED", "OUT_OF_SCOPE", "MISSING"}
    missing = []
    deferred = []

    for i, item in enumerate(coverage):
        if not isinstance(item, dict):
            print(f"ERROR: Coverage item {i+1} must be an object", file=sys.stderr)
            sys.exit(1)

        for field in ("requirement", "status"):
            if field not in item:
                print(f"ERROR: Coverage item {i+1} missing required field '{field}'", file=sys.stderr)
                sys.exit(1)

        st = item["status"].upper()
        item["status"] = st

        if st not in valid_statuses:
            print(f"ERROR: Coverage item {i+1} status must be one of {sorted(valid_statuses)} (got '{st}')",
                  file=sys.stderr)
            sys.exit(1)

        if st in ("DEFERRED", "OUT_OF_SCOPE") and not item.get("reason"):
            print(f"ERROR: Coverage item {i+1} '{item['requirement'][:50]}' has status {st} but no reason.",
                  file=sys.stderr)
            sys.exit(1)

        if st == "MISSING":
            missing.append(item)
        elif st in ("DEFERRED", "OUT_OF_SCOPE"):
            deferred.append(item)

    return coverage, len(missing), deferred


def cmd_draft_plan(args):
    """Store a draft plan for user review before materializing into pipeline."""
    tracker = load_tracker(args.project)

    try:
        draft_tasks = load_json_data(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(draft_tasks, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    # Validate against add-tasks contract
    errors = validate_contract(CONTRACTS["add-tasks"], draft_tasks)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    # Readiness gate: check assumptions if provided
    assumptions = None
    high_count = 0
    assumptions_raw = getattr(args, "assumptions", None)
    if assumptions_raw:
        assumptions, high_count = _check_assumptions_readiness(assumptions_raw)
        if high_count >= 5:
            print(f"ERROR: Readiness gate FAILED — {high_count} HIGH-severity assumptions.", file=sys.stderr)
            print("A plan built on 5+ unverified assumptions is not a plan. Clarify before planning:", file=sys.stderr)
            for a in assumptions:
                if a["severity"] == "HIGH":
                    print(f"  - {a['assumption']} (basis: {a['basis']})", file=sys.stderr)
            sys.exit(1)

    # Coverage gate: check all source requirements are accounted for
    coverage = None
    coverage_deferred = []
    coverage_raw = getattr(args, "coverage", None)
    if coverage_raw:
        coverage, missing_count, coverage_deferred = _check_coverage(coverage_raw)
        if missing_count > 0:
            print(f"ERROR: Coverage gate FAILED — {missing_count} requirement(s) with status MISSING.",
                  file=sys.stderr)
            print("Every source requirement must be COVERED by a task, or explicitly DEFERRED/OUT_OF_SCOPE with a reason:",
                  file=sys.stderr)
            for item in coverage:
                if item["status"] == "MISSING":
                    print(f"  MISSING: {item['requirement']}", file=sys.stderr)
            sys.exit(1)

    # Store draft (overwrite previous draft)
    tracker["draft_plan"] = {
        "source_idea_id": args.idea if hasattr(args, "idea") and args.idea else None,
        "source_objective_id": args.objective if hasattr(args, "objective") and args.objective else None,
        "created": now_iso(),
        "tasks": draft_tasks,
        "assumptions": assumptions,
        "coverage": coverage,
    }

    save_tracker(args.project, tracker)

    # AC quality warnings (non-blocking at draft time — shows errors for user to fix)
    _warn_ac_quality(draft_tasks)

    # Reference validation (non-blocking at draft time)
    ref_warnings = _validate_plan_references(draft_tasks, args.project)
    if ref_warnings:
        print()
        print(f"**REFERENCE WARNINGS** ({len(ref_warnings)}):")
        for w in ref_warnings:
            print(w)
        print("Tip: fix invalid origins/scopes/knowledge_ids before approving.")
        print()

    # Assumptions warnings
    if assumptions and 3 <= high_count <= 4:
        print(f"**ASSUMPTION WARNING**: {high_count} HIGH-severity assumptions — verify before Phase 1.")
        for a in assumptions:
            if a["severity"] == "HIGH":
                print(f"  - {a['assumption']}")
        print()

    # Coverage summary
    if coverage_deferred:
        print(f"**DEFERRED/OUT_OF_SCOPE** ({len(coverage_deferred)}):")
        for item in coverage_deferred:
            print(f"  [{item['status']}] {item['requirement']}: {item.get('reason', '')}")
        print()

    print(f"## Draft Plan: {args.project}")
    if tracker["draft_plan"]["source_idea_id"]:
        print(f"Source idea: {tracker['draft_plan']['source_idea_id']}")
    if tracker["draft_plan"].get("source_objective_id"):
        print(f"Source objective: {tracker['draft_plan']['source_objective_id']}")
    print(f"Tasks in draft: {len(draft_tasks)}")
    if assumptions:
        high = sum(1 for a in assumptions if a["severity"] == "HIGH")
        med = sum(1 for a in assumptions if a["severity"] == "MED")
        low = sum(1 for a in assumptions if a["severity"] == "LOW")
        print(f"Assumptions: {len(assumptions)} ({high} HIGH, {med} MED, {low} LOW)")
    if coverage:
        covered = sum(1 for c in coverage if c["status"] == "COVERED")
        deferred = sum(1 for c in coverage if c["status"] in ("DEFERRED", "OUT_OF_SCOPE"))
        print(f"Coverage: {covered} covered, {deferred} deferred/out-of-scope, {len(coverage)} total requirements")
    print()

    _print_draft_tasks(draft_tasks)

    print()
    print("**This is a DRAFT. Tasks are NOT yet in the pipeline.**")
    print("Review the plan above, then:")
    print("  - `python -m core.pipeline approve-plan {project}` — materialize into pipeline")
    print("  - `python -m core.pipeline show-draft {project}` — view again")
    print("  - `python -m core.pipeline draft-plan {project} --data '...'` — replace with new draft")


def cmd_show_draft(args):
    """Show the current draft plan."""
    tracker = load_tracker(args.project)
    draft = tracker.get("draft_plan")

    if not draft or not draft.get("tasks"):
        print(f"No draft plan for '{args.project}'.")
        return

    print(f"## Draft Plan: {args.project}")
    if draft.get("source_idea_id"):
        print(f"Source idea: {draft['source_idea_id']}")
    if draft.get("source_objective_id"):
        print(f"Source objective: {draft['source_objective_id']}")
    print(f"Created: {draft.get('created', '')}")
    print(f"Tasks: {len(draft['tasks'])}")
    print()

    _print_draft_tasks(draft["tasks"])

    print()
    print("**DRAFT — not yet in pipeline.**")
    print("Run `approve-plan` to materialize, or `draft-plan` to replace.")


def cmd_approve_plan(args):
    """Approve draft plan: materialize tasks into pipeline and mark idea COMMITTED."""
    mapping = {}
    entries = []

    # Atomic section: lock → load → remap → validate → save
    with tracker_lock(args.project):
        tracker = load_tracker(args.project)
        draft = tracker.get("draft_plan")

        if not draft or not draft.get("tasks"):
            print(f"ERROR: No draft plan for '{args.project}'.", file=sys.stderr)
            sys.exit(1)

        draft_tasks = draft["tasks"]
        source_idea_id = draft.get("source_idea_id")
        source_objective_id = draft.get("source_objective_id")

        # Remap temporary IDs
        mapping = _remap_temp_ids(draft_tasks, tracker["tasks"])

        # Check for duplicate IDs against existing tasks (after remap)
        existing_ids = {t["id"] for t in tracker["tasks"]}
        for t in draft_tasks:
            if t["id"] in existing_ids:
                print(f"ERROR: Duplicate task ID '{t['id']}' — already exists in pipeline.",
                      file=sys.stderr)
                sys.exit(1)

        # Build task entries (same logic as cmd_add_tasks)
        entries = []
        for t in draft_tasks:
            entry = _build_task_entry(t, source_idea_id=source_idea_id,
                                      source_objective_id=source_objective_id)
            entries.append(entry)

        # AC hard gate: feature/bug tasks must have acceptance criteria
        has_ac_errors = _warn_ac_quality(entries)
        if has_ac_errors:
            print("ERROR: Cannot approve plan — feature/bug tasks without acceptance criteria.",
                  file=sys.stderr)
            sys.exit(1)

        # Reference validation (non-blocking warnings)
        ref_warnings = _validate_plan_references(entries, args.project)
        if ref_warnings:
            print(f"**REFERENCE WARNINGS** ({len(ref_warnings)}):", file=sys.stderr)
            for w in ref_warnings:
                print(w, file=sys.stderr)

        # Validate DAG
        all_tasks = tracker["tasks"] + entries
        dag_errors = validate_dag(all_tasks)
        if dag_errors:
            print(f"ERROR: Task graph validation failed:", file=sys.stderr)
            for e in dag_errors:
                print(f"  {e}", file=sys.stderr)
            sys.exit(1)

        # Materialize
        tracker["tasks"].extend(entries)
        tracker["plan_approved_at"] = now_iso()

        # Clear draft
        tracker.pop("draft_plan", None)

        save_tracker(args.project, tracker)

    # Print ID mapping (outside lock)
    if mapping:
        print("ID mapping:")
        for temp, real in sorted(mapping.items()):
            print(f"  {temp} -> {real}")

    # Mark source idea as COMMITTED (outside lock — separate entity)
    if source_idea_id:
        _s = _get_storage()
        if _s.exists(args.project, 'ideas'):
            ideas_data = _s.load_data(args.project, 'ideas')
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == source_idea_id:
                    if idea["status"] == "APPROVED":
                        idea["status"] = "COMMITTED"
                        idea["committed_at"] = now_iso()
                        idea["updated"] = now_iso()
                        _s.save_data(args.project, 'ideas', ideas_data)
                        print(f"Idea {source_idea_id} marked as COMMITTED.")
                    elif idea["status"] == "COMMITTED":
                        pass  # already committed
                    else:
                        print(f"WARNING: Idea {source_idea_id} is {idea['status']}, "
                              f"expected APPROVED. Not changing status.",
                              file=sys.stderr)
                    break

    print(f"## Plan approved: {args.project}")
    print(f"Materialized {len(entries)} tasks into pipeline.")
    print()
    print_task_list(tracker)
    print(f"\nRun `next {args.project}` to start execution.")


def _print_draft_tasks(tasks: list):
    """Print draft tasks in a readable format."""
    print("| # | ID | Name | Dependencies | Type | Scopes |")
    print("|---|-----|------|-------------|------|--------|")
    for i, t in enumerate(tasks, 1):
        deps = ", ".join(t.get("depends_on", [])) or "—"
        task_type = t.get("type", "feature")
        scopes = ", ".join(t.get("scopes", [])) or "—"
        print(f"| {i} | {t['id']} | {t['name']} | {deps} | {task_type} | {scopes} |")

    # Show details
    print()
    for t in tasks:
        print(f"### {t['id']}: {t['name']}")
        if t.get("description"):
            print(f"  {t['description']}")
        if t.get("instruction"):
            print(f"  **Instruction**: {t['instruction'][:100]}...")
        if t.get("acceptance_criteria"):
            print(f"  **Acceptance criteria**: {len(t['acceptance_criteria'])} items")
            for ac in t["acceptance_criteria"]:
                if isinstance(ac, dict):
                    text = ac.get("text", "")
                    tmpl = ac.get("from_template")
                    print(f"    - {text}" + (f" (from {tmpl})" if tmpl else ""))
                else:
                    print(f"    - {ac}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Forge Pipeline -- task graph orchestrator"
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("init", help="Create project tracker")
    p.add_argument("project")
    p.add_argument("--goal", required=True, help="Project goal description")
    p.add_argument("--force", action="store_true", help="Overwrite existing")

    p = sub.add_parser("add-tasks", help="Add tasks to graph")
    p.add_argument("project")
    p.add_argument("--data", required=True, help="JSON array of tasks")

    p = sub.add_parser("next", help="Get next task")
    p.add_argument("project")
    p.add_argument("--agent", default=None, help="Agent name for multi-agent claim")

    p = sub.add_parser("begin", help="Claim next task and show full execution context")
    p.add_argument("project")
    p.add_argument("--agent", default=None, help="Agent name for multi-agent claim")
    p.add_argument("--lean", action="store_true", default=False,
                   help="Lean context: skip Knowledge, Research, Business Context, Lessons")

    p = sub.add_parser("complete", help="Mark task DONE")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--agent", default=None, help="Agent name (verified against claim)")
    p.add_argument("--force", action="store_true", help="Complete even without changes or with failed gates")
    p.add_argument("--reasoning", default=None, help="Why these changes were made (used for auto-recorded changes)")
    p.add_argument("--ac-reasoning", default=None, dest="ac_reasoning",
                   help="Justification that acceptance criteria are met (required when task has AC)")
    p.add_argument("--deferred", default=None,
                   help="JSON array of {requirement, reason} — items deferred from source doc. Auto-creates OPEN decisions.")

    p = sub.add_parser("fail", help="Mark task FAILED")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--reason", default=None)
    p.add_argument("--agent", default=None, help="Agent name")

    p = sub.add_parser("skip", help="Mark task SKIPPED (requires --reason)")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--reason", required=True, help="Why this task is being skipped (min 50 chars)")
    p.add_argument("--force", action="store_true", help="Required for feature/bug tasks")

    p = sub.add_parser("status", help="Status dashboard")
    p.add_argument("project")

    p = sub.add_parser("list", help="List all tasks")
    p.add_argument("project")

    p = sub.add_parser("reset", help="Reset tasks from ID onward")
    p.add_argument("project")
    p.add_argument("--from", dest="from_task", required=True)

    p = sub.add_parser("update-task", help="Update an existing task")
    p.add_argument("project")
    p.add_argument("--data", required=True, help="JSON object with id + fields to update")

    p = sub.add_parser("remove-task", help="Remove a TODO task")
    p.add_argument("project")
    p.add_argument("task_id")

    p = sub.add_parser("context", help="Aggregated context for a task")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--lean", action="store_true", default=False,
                   help="Lean mode: skip Knowledge, Research, Business Context, Lessons")

    p = sub.add_parser("config", help="Set/show project configuration")
    p.add_argument("project")
    p.add_argument("--data", default=None, help="JSON object with config keys")

    p = sub.add_parser("draft-plan", help="Store draft plan for review")
    p.add_argument("project")
    p.add_argument("--data", required=True, help="JSON array of tasks (same format as add-tasks)")
    p.add_argument("--idea", default=None, help="Source idea ID (I-NNN)")
    p.add_argument("--objective", default=None, help="Source objective ID (O-NNN)")
    p.add_argument("--assumptions", default=None,
                   help="JSON array of {assumption, basis, severity} for readiness gate")
    p.add_argument("--coverage", default=None,
                   help="JSON array of {requirement, source, covered_by, status, reason?} for coverage gate")

    p = sub.add_parser("show-draft", help="Show current draft plan")
    p.add_argument("project")

    p = sub.add_parser("approve-plan", help="Approve draft plan and materialize into pipeline")
    p.add_argument("project")

    p = sub.add_parser("contract", help="Print contract spec (no project needed)")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))
    p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)

    p = sub.add_parser("register-subtasks", help="Register subtasks")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--data", required=True, help="JSON array [{id, name, ...}]")

    p = sub.add_parser("complete-subtask", help="Mark subtask DONE")
    p.add_argument("project")
    p.add_argument("subtask_id")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "init": cmd_init,
        "add-tasks": cmd_add_tasks,
        "next": cmd_next,
        "begin": cmd_begin,
        "complete": cmd_complete,
        "fail": cmd_fail,
        "skip": cmd_skip,
        "status": cmd_status,
        "list": cmd_list,
        "reset": cmd_reset,
        "update-task": cmd_update_task,
        "remove-task": cmd_remove_task,
        "context": cmd_context,
        "config": cmd_config,
        "draft-plan": cmd_draft_plan,
        "show-draft": cmd_show_draft,
        "approve-plan": cmd_approve_plan,
        "contract": lambda args: print(render_contract(args.name, CONTRACTS[args.name])),
        "register-subtasks": cmd_register_subtasks,
        "complete-subtask": cmd_complete_subtask,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
