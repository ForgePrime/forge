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
from datetime import datetime, timezone
from pathlib import Path

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
    path.parent.mkdir(parents=True, exist_ok=True)
    tracker["updated"] = now_iso()
    path.write_text(
        json.dumps(tracker, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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

    # Validate required fields
    existing_ids = {t["id"] for t in tracker["tasks"]}
    for t in new_tasks:
        if "id" not in t or "name" not in t:
            print(f"ERROR: Each task must have 'id' and 'name'", file=sys.stderr)
            sys.exit(1)
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


def cmd_next(args):
    """Get next TODO task or subtask respecting dependencies."""
    tracker = load_tracker(args.project)

    if not tracker["tasks"]:
        print(f"## No tasks in project '{args.project}'")
        print(f"\nAdd tasks with `add-tasks` or run `/plan {args.project}`")
        return

    done_ids = {t["id"] for t in tracker["tasks"]
                if t["status"] in ("DONE", "SKIPPED")}

    # Check if something is IN_PROGRESS
    in_progress = [t for t in tracker["tasks"] if t["status"] == "IN_PROGRESS"]
    if in_progress:
        task = in_progress[0]
        if task.get("has_subtasks"):
            _next_subtask(args.project, tracker, task)
            return
        print(f"## Current task: {task['id']} — {task['name']}")
        print(f"")
        print(f"Status: **IN_PROGRESS** (started: {task['started_at']})")
        print(f"")
        print_task_detail(task)
        return

    # Find next TODO with all dependencies met
    for task in tracker["tasks"]:
        if task["status"] != "TODO":
            continue
        deps_met = all(dep in done_ids for dep in task["depends_on"])
        if deps_met:
            task["status"] = "IN_PROGRESS"
            task["started_at"] = now_iso()
            save_tracker(args.project, tracker)

            print(f"## Next task: {task['id']} — {task['name']}")
            print(f"")
            print(f"Status: TODO -> **IN_PROGRESS**")
            print(f"")
            print_task_detail(task)
            return

    # All done or blocked
    all_done = all(t["status"] in ("DONE", "SKIPPED") for t in tracker["tasks"])
    if all_done:
        print(f"## Project complete: {args.project}")
        print(f"")
        print(f"All {len(tracker['tasks'])} tasks finished.")
        print_status(args.project, tracker)
    else:
        failed = [t for t in tracker["tasks"] if t["status"] == "FAILED"]
        if failed:
            print(f"## Project blocked: {args.project}")
            print(f"")
            for t in failed:
                print(f"  FAILED: {t['id']} {t['name']}: {t['failed_reason']}")
        else:
            print(f"## No tasks available (dependencies not met)")
            print_status(args.project, tracker)


def cmd_complete(args):
    """Mark task as DONE."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)

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
        line = f"  {icon} {task['id']} {task['name']}"
        if task["status"] == "IN_PROGRESS":
            if task.get("has_subtasks"):
                line += f" <- current [{task.get('subtask_done', 0)}/{task.get('subtask_total', 0)} subtasks]"
            else:
                line += " <- current"
        elif task["status"] == "FAILED":
            line += f" -- {task.get('failed_reason', '')}"
        print(line)


def print_task_list(tracker: dict):
    """Print all tasks as MD table."""
    print("| # | ID | Name | Status | Depends On | Skill |")
    print("|---|-----|------|--------|------------|-------|")
    for i, task in enumerate(tracker["tasks"], 1):
        deps = ", ".join(task["depends_on"]) if task["depends_on"] else "--"
        skill = task.get("skill", "--") or "--"
        icon = STATUS_ICONS.get(task["status"], "?")
        print(f"| {i} | {task['id']} | {task['name']} | {icon} {task['status']} | {deps} | {skill} |")


def print_task_detail(task: dict):
    """Print full task detail."""
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
    print(f"")
    print(f"When done: `python -m core.pipeline complete {{project}} {task['id']}`")


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

    p = sub.add_parser("complete", help="Mark task DONE")
    p.add_argument("project")
    p.add_argument("task_id")

    p = sub.add_parser("fail", help="Mark task FAILED")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--reason", default=None)

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
