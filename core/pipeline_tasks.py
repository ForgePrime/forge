"""Pipeline task CRUD — init, add, update, remove, subtasks, reset."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import (
    _get_storage, _trace, _max_task_num, load_tracker, save_tracker,
    find_task, print_status, print_task_list, print_task_detail,
)
from contracts import render_contract, validate_contract
from storage import JSONFileStorage, load_json_data, now_iso, tracker_lock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
