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
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract, atomic_write_json

CLAIM_WAIT_SECONDS = 1.5

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


# -- Paths --

def output_dir(project: str) -> Path:
    return Path("forge_output") / project


def tracker_path(project: str) -> Path:
    return output_dir(project) / "tracker.json"


# -- Time --

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -- Tracker I/O --

def load_tracker(project: str) -> dict:
    path = tracker_path(project)
    if not path.exists():
        print(f"ERROR: No tracker for project '{project}'. Run: init {project} --goal \"...\"", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_tracker(project: str, tracker: dict):
    path = tracker_path(project)
    tracker["updated"] = now_iso()
    atomic_write_json(path, tracker)


def find_task(tracker: dict, task_id: str) -> dict:
    for task in tracker["tasks"]:
        if task["id"] == task_id:
            return task
    print(f"ERROR: Task '{task_id}' not found.", file=sys.stderr)
    sys.exit(1)


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
                      "type", "blocked_by_decisions"],
        "enums": {
            "type": {"feature", "bug", "chore", "investigation"},
        },
        "types": {
            "depends_on": list,
            "conflicts_with": list,
            "parallel": bool,
            "acceptance_criteria": list,
            "blocked_by_decisions": list,
        },
        "invariant_texts": [
            "id: unique task identifier (e.g., T-001)",
            "name: kebab-case descriptive name (e.g., setup-database-schema)",
            "description: WHAT needs to be done (concrete, not vague)",
            "instruction: HOW to do it (step-by-step, mention specific files)",
            "depends_on: list of prerequisite task IDs (must exist)",
            "parallel: true if this task can run alongside others",
            "conflicts_with: list of task IDs that modify same files",
            "acceptance_criteria: list of concrete conditions that must be true when task is DONE",
            "type: task category — feature (default), bug, chore, or investigation",
            "blocked_by_decisions: list of decision IDs (D-001, etc.) that must be CLOSED before this task can start",
        ],
        "example": [
            {
                "id": "T-001",
                "name": "setup-database-schema",
                "description": "Create the database schema for user authentication",
                "instruction": "Create migrations/001_auth.sql with users and sessions tables. Follow existing migration patterns.",
                "depends_on": [],
                "parallel": False,
                "type": "feature",
                "acceptance_criteria": [
                    "migrations/001_auth.sql exists with users and sessions tables",
                    "Migration runs without errors on empty database",
                ],
            },
            {
                "id": "T-002",
                "name": "implement-auth-middleware",
                "description": "JWT validation middleware",
                "instruction": "Create src/middleware/auth.ts with RS256 JWT validation. Use jsonwebtoken library.",
                "depends_on": ["T-001"],
                "parallel": False,
                "conflicts_with": ["T-003"],
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
                      "type", "blocked_by_decisions"],
        "enums": {
            "type": {"feature", "bug", "chore", "investigation"},
        },
        "types": {
            "depends_on": list,
            "conflicts_with": list,
            "acceptance_criteria": list,
            "blocked_by_decisions": list,
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
    "config": {
        "required": [],
        "optional": ["test_cmd", "lint_cmd", "typecheck_cmd", "branch_prefix"],
        "enums": {},
        "types": {},
        "invariant_texts": [
            "test_cmd: shell command to run tests (e.g., 'pytest', 'npm test')",
            "lint_cmd: shell command to run linter (e.g., 'ruff check .', 'npm run lint')",
            "typecheck_cmd: shell command for type checking (e.g., 'mypy src/', 'npx tsc --noEmit')",
            "branch_prefix: prefix for git branches (e.g., 'forge/')",
            "Config is a flat JSON object, not an array",
        ],
        "example": [
            {
                "test_cmd": "pytest",
                "lint_cmd": "ruff check .",
                "branch_prefix": "forge/",
            },
        ],
    },
}


# -- Commands --

def cmd_init(args):
    """Create a new project tracker."""
    path = tracker_path(args.project)
    if path.exists() and not args.force:
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
    print(f"Saved to: {path}")
    print(f"")
    print(f"Next: Add tasks with `add-tasks` or run `/plan {args.project}` to decompose the goal.")


def cmd_add_tasks(args):
    """Add tasks to the project graph."""
    tracker = load_tracker(args.project)

    try:
        new_tasks = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_tasks, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    # Contract validation
    errors = validate_contract(CONTRACTS["add-tasks"], new_tasks)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    # Check for duplicate IDs
    existing_ids = {t["id"] for t in tracker["tasks"]}
    for t in new_tasks:
        if t["id"] in existing_ids:
            print(f"ERROR: Duplicate task ID '{t['id']}'", file=sys.stderr)
            sys.exit(1)

    # Build task entries
    entries = []
    for t in new_tasks:
        entries.append({
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
            "status": "TODO",
            "started_at": None,
            "completed_at": None,
            "failed_reason": None,
        })

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

    print(f"Added {len(entries)} tasks to '{args.project}'")
    print_task_list(tracker)
    print(f"\nRun `next {args.project}` to start.")


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
    dpath = Path("forge_output") / project / "decisions.json"
    if not dpath.exists():
        return set()
    data = json.loads(dpath.read_text(encoding="utf-8"))
    return {d["id"] for d in data.get("decisions", []) if d.get("status") == "OPEN"}


def _blocked_by_open_decisions(task: dict, open_decision_ids: set) -> list:
    """Return list of OPEN decision IDs that block this task."""
    required = set(task.get("blocked_by_decisions", []))
    if not required:
        return []
    return sorted(required & open_decision_ids)


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
        return

    done_ids = {t["id"] for t in tracker["tasks"]
                if t["status"] in ("DONE", "SKIPPED")}
    active_ids = _get_active_ids(tracker)

    # Check if THIS agent already has a task IN_PROGRESS
    for task in tracker["tasks"]:
        if task["status"] == "IN_PROGRESS" and task.get("agent") == agent:
            if task.get("has_subtasks"):
                _next_subtask(args.project, tracker, task)
                return
            print(f"## Current task: {task['id']} — {task['name']}")
            print(f"Agent: {agent}")
            print(f"Status: **IN_PROGRESS** (started: {task['started_at']})")
            print()
            print_task_detail(task)
            return

    # Check if ANY task is IN_PROGRESS without an agent (single-agent compat)
    for task in tracker["tasks"]:
        if task["status"] == "IN_PROGRESS" and not task.get("agent"):
            if task.get("has_subtasks"):
                _next_subtask(args.project, tracker, task)
                return
            print(f"## Current task: {task['id']} — {task['name']}")
            print(f"Status: **IN_PROGRESS** (started: {task['started_at']})")
            print()
            print_task_detail(task)
            return

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
        return

    # --- Phase 1: CLAIMING ---
    candidate["status"] = "CLAIMING"
    candidate["agent"] = agent
    candidate["claimed_at"] = now_iso()
    save_tracker(args.project, tracker)

    # --- Wait ---
    time.sleep(CLAIM_WAIT_SECONDS)

    # --- Phase 2: Verify claim ---
    tracker = load_tracker(args.project)
    task = find_task(tracker, candidate["id"])

    if task["status"] != "CLAIMING" or task.get("agent") != agent:
        # Another agent claimed it — back off
        print(f"## Claim conflict on {candidate['id']}")
        print(f"Agent '{agent}' lost claim to agent '{task.get('agent', '?')}'.")
        print(f"Retrying with next available task...")
        # Recursive retry — will find the next candidate
        cmd_next(args)
        return

    # Claim won — promote to IN_PROGRESS
    task["status"] = "IN_PROGRESS"
    task["started_at"] = now_iso()
    save_tracker(args.project, tracker)

    print(f"## Next task: {task['id']} — {task['name']}")
    print(f"Agent: {agent}")
    print(f"Status: TODO -> CLAIMING -> **IN_PROGRESS**")
    print()
    print_task_detail(task)


def cmd_complete(args):
    """Mark task as DONE."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)
    agent = getattr(args, "agent", None)

    # Verify agent ownership if task was claimed
    if task.get("agent") and agent and task["agent"] != agent:
        print(f"WARNING: Task {args.task_id} is owned by agent '{task['agent']}', "
              f"not '{agent}'. Completing anyway.", file=sys.stderr)

    task["status"] = "DONE"
    task["completed_at"] = now_iso()
    save_tracker(args.project, tracker)

    done_count = sum(1 for t in tracker["tasks"] if t["status"] in ("DONE", "SKIPPED"))
    total = len(tracker["tasks"])
    print(f"Task {args.task_id} ({task['name']}): -> DONE  [{done_count}/{total}]")


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
    """Mark task as SKIPPED."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)

    task["status"] = "SKIPPED"
    task["completed_at"] = now_iso()
    save_tracker(args.project, tracker)

    done_count = sum(1 for t in tracker["tasks"] if t["status"] in ("DONE", "SKIPPED"))
    total = len(tracker["tasks"])
    print(f"Task {args.task_id} ({task['name']}): -> SKIPPED  [{done_count}/{total}]")


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
    tracker = load_tracker(args.project)

    try:
        updates = json.loads(args.data)
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

    task = find_task(tracker, updates["id"])

    if task["status"] in ("IN_PROGRESS", "DONE"):
        print(f"ERROR: Cannot update task {updates['id']} — status is {task['status']}. "
              f"Reset it first.", file=sys.stderr)
        sys.exit(1)

    # Apply updates (only provided fields)
    updatable = ["name", "description", "instruction", "depends_on",
                 "conflicts_with", "skill", "acceptance_criteria",
                 "type", "blocked_by_decisions"]
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
        raw = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
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

    ac = task.get("acceptance_criteria", [])
    if ac:
        print(f"")
        print(f"**Acceptance Criteria**:")
        for criterion in ac:
            print(f"  - [ ] {criterion}")

    print(f"")
    print(f"When done: `python -m core.pipeline complete {{project}} {task['id']}`")


# -- Context & Config Commands --

def _estimate_context_size(project: str, task_ids: set) -> int:
    """Estimate context size in characters for the given dependency tasks."""
    total = 0
    for fname in ("changes.json", "decisions.json", "lessons.json"):
        fpath = Path("forge_output") / project / fname
        if fpath.exists():
            data = json.loads(fpath.read_text(encoding="utf-8"))
            key = fname.replace(".json", "")
            for entry in data.get(key, []):
                if entry.get("task_id") in task_ids:
                    total += len(json.dumps(entry))
    return total


def cmd_context(args):
    """Show aggregated context for a task: dependency outputs, decisions, changes."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)

    print(f"## Context for {args.task_id}: {task['name']}")
    print()

    # Task details
    if task.get("description"):
        print(f"**Description**: {task['description']}")
    if task.get("instruction"):
        print(f"**Instruction**: {task['instruction']}")
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
            print()

        # Show changes from dependency tasks
        changes_file = Path("forge_output") / args.project / "changes.json"
        if changes_file.exists():
            changes_data = json.loads(changes_file.read_text(encoding="utf-8"))
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

        # Show decisions from dependency tasks
        decisions_file = Path("forge_output") / args.project / "decisions.json"
        if decisions_file.exists():
            dec_data = json.loads(decisions_file.read_text(encoding="utf-8"))
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
    decisions_file = Path("forge_output") / args.project / "decisions.json"
    if decisions_file.exists():
        dec_data = json.loads(decisions_file.read_text(encoding="utf-8"))
        task_decisions = [d for d in dec_data.get("decisions", [])
                          if d.get("task_id") == args.task_id]
        if task_decisions:
            print(f"### Existing Decisions for This Task")
            print()
            for d in task_decisions:
                print(f"- **{d['id']}** ({d.get('status', '')}): {d.get('issue', '')}")
            print()

    # Show relevant lessons
    lessons_file = Path("forge_output") / args.project / "lessons.json"
    if lessons_file.exists():
        lessons_data = json.loads(lessons_file.read_text(encoding="utf-8"))
        lessons = lessons_data.get("lessons", [])
        if lessons:
            print(f"### Relevant Lessons")
            print()
            for l in lessons:
                print(f"- **{l['id']}** [{l.get('severity', '')}]: {l['title']}")
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
            config = json.loads(args.data)
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


# -- CLI --

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

    p = sub.add_parser("complete", help="Mark task DONE")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--agent", default=None, help="Agent name (verified against claim)")

    p = sub.add_parser("fail", help="Mark task FAILED")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--reason", default=None)
    p.add_argument("--agent", default=None, help="Agent name")

    p = sub.add_parser("skip", help="Mark task SKIPPED")
    p.add_argument("project")
    p.add_argument("task_id")

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

    p = sub.add_parser("config", help="Set/show project configuration")
    p.add_argument("project")
    p.add_argument("--data", default=None, help="JSON object with config keys")

    p = sub.add_parser("contract", help="Print contract spec")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))

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
