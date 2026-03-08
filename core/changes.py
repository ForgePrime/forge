"""
Changes — track every code modification with full context.

This is NEW — Skill_v1 didn't have this because it tracked field resolutions,
not code changes. This module fills the gap between git (WHAT changed) and
decisions (WHY we chose this approach) by recording the actual execution context.

Every change record captures:
- WHAT file was modified and how (create/edit/delete)
- WHY this change was made (linked to task + decision)
- HOW the agent reasoned about it (reasoning_trace)
- WHO made or approved it (claude/user)

Usage:
    python -m core.changes <command> <project> [options]

Commands:
    record   {project} --data '{json}'    Record changes
    read     {project} [--task X]         Read change log
    summary  {project}                    Summary statistics
    contract                              Print contract spec
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract, atomic_write_json

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


# -- Paths --

def changes_path(project: str) -> Path:
    return Path("forge_output") / project / "changes.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_or_create(project: str) -> dict:
    path = changes_path(project)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "project": project,
        "updated": now_iso(),
        "changes": [],
    }


def save_json(project: str, data: dict):
    path = changes_path(project)
    data["updated"] = now_iso()
    atomic_write_json(path, data)


# -- Contract --

CONTRACTS = {
    "record": {
        "required": ["task_id", "file", "action", "summary"],
        "optional": ["reasoning_trace", "decision_ids", "lines_added",
                      "lines_removed", "group_id"],
        "enums": {
            "action": {"create", "edit", "delete", "rename", "move"},
        },
        "types": {
            "reasoning_trace": list,
            "decision_ids": list,
            "lines_added": int,
            "lines_removed": int,
        },
        "invariant_texts": [
            "task_id must reference an existing task in the pipeline",
            "file must be a relative path from project root",
            "reasoning_trace: array of {step, detail} objects explaining the change",
            "decision_ids: list of D-NNN IDs that led to this change",
            "group_id: links related changes across files (e.g. a refactor touching 5 files)",
        ],
        "example": [
            {
                "task_id": "T-003",
                "file": "src/middleware/auth.ts",
                "action": "create",
                "summary": "JWT validation middleware with RS256 support",
                "reasoning_trace": [
                    {"step": "design", "detail": "Chose middleware pattern over per-route guards for DRY"},
                    {"step": "implementation", "detail": "Used jsonwebtoken library, RS256 algorithm per D-001"},
                    {"step": "security", "detail": "Added token expiry check, audience validation"},
                ],
                "decision_ids": ["D-001"],
                "lines_added": 45,
            },
            {
                "task_id": "T-003",
                "file": "src/routes/api.ts",
                "action": "edit",
                "summary": "Added auth middleware to protected routes",
                "reasoning_trace": [
                    {"step": "integration", "detail": "Applied middleware to /api/* routes, excluded /api/health"},
                ],
                "decision_ids": ["D-001"],
                "group_id": "auth-middleware-integration",
                "lines_added": 3,
                "lines_removed": 1,
            },
        ],
    },
}


# -- Commands --

def cmd_record(args):
    """Record change entries."""
    try:
        new_changes = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_changes, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["record"], new_changes)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    # Cross-validate: check task_ids and decision_ids exist
    tracker_file = Path("forge_output") / args.project / "tracker.json"
    decisions_file = Path("forge_output") / args.project / "decisions.json"
    valid_task_ids = set()
    valid_decision_ids = set()
    if tracker_file.exists():
        tracker = json.loads(tracker_file.read_text(encoding="utf-8"))
        valid_task_ids = {t["id"] for t in tracker.get("tasks", [])}
    if decisions_file.exists():
        dec_data = json.loads(decisions_file.read_text(encoding="utf-8"))
        valid_decision_ids = {d["id"] for d in dec_data.get("decisions", [])}

    for c in new_changes:
        tid = c.get("task_id", "")
        if valid_task_ids and tid not in valid_task_ids:
            print(f"WARNING: task_id '{tid}' not found in pipeline.", file=sys.stderr)
        for did in c.get("decision_ids", []):
            if valid_decision_ids and did not in valid_decision_ids:
                print(f"WARNING: decision_id '{did}' not found in decisions.json.", file=sys.stderr)

    data = load_or_create(args.project)
    timestamp = now_iso()

    # Find next C-NNN ID
    existing_ids = [
        int(c["id"].split("-")[1]) for c in data.get("changes", [])
        if c.get("id", "").startswith("C-")
    ]
    next_id = max(existing_ids, default=0) + 1

    recorded = []
    for c in new_changes:
        change = {
            "id": f"C-{next_id:03d}",
            "task_id": c["task_id"],
            "file": c["file"],
            "action": c["action"],
            "summary": c["summary"],
            "reasoning_trace": c.get("reasoning_trace", []),
            "decision_ids": c.get("decision_ids", []),
            "lines_added": c.get("lines_added", 0),
            "lines_removed": c.get("lines_removed", 0),
            "group_id": c.get("group_id", ""),
            "timestamp": timestamp,
        }
        data["changes"].append(change)
        recorded.append(change["id"])
        next_id += 1

    save_json(args.project, data)

    print(f"Changes recorded: {args.project}")
    print(f"  Added: {len(recorded)} ({', '.join(recorded)})")
    print(f"  Total: {len(data['changes'])}")


def cmd_read(args):
    """Read change log."""
    path = changes_path(args.project)
    if not path.exists():
        print(f"No changes recorded for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    changes = data.get("changes", [])

    if args.task:
        changes = [c for c in changes if c.get("task_id") == args.task]

    print(f"## Changes: {args.project}")
    if args.task:
        print(f"Filter: task={args.task}")
    print(f"Count: {len(changes)}")
    print()

    if not changes:
        print("(none)")
        return

    print("| ID | Task | File | Action | Summary | Decisions |")
    print("|----|------|------|--------|---------|-----------|")
    for c in changes:
        summary = c.get("summary", "")[:40]
        decs = ", ".join(c.get("decision_ids", [])) or "--"
        print(f"| {c['id']} | {c['task_id']} | {c['file']} | {c['action']} | {summary} | {decs} |")


def cmd_summary(args):
    """Summary statistics."""
    path = changes_path(args.project)
    if not path.exists():
        print(f"No changes recorded for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    changes = data.get("changes", [])

    # Stats
    by_action = {}
    by_task = {}
    total_added = 0
    total_removed = 0
    files_touched = set()

    for c in changes:
        action = c.get("action", "unknown")
        by_action[action] = by_action.get(action, 0) + 1
        task = c.get("task_id", "unknown")
        by_task[task] = by_task.get(task, 0) + 1
        total_added += c.get("lines_added", 0)
        total_removed += c.get("lines_removed", 0)
        files_touched.add(c.get("file", ""))

    print(f"## Change Summary: {args.project}")
    print()
    print(f"| Metric | Value |")
    print(f"|--------|-------|")
    print(f"| Total changes | {len(changes)} |")
    print(f"| Files touched | {len(files_touched)} |")
    print(f"| Lines added | {total_added} |")
    print(f"| Lines removed | {total_removed} |")
    print()
    print("### By action")
    for action, count in sorted(by_action.items()):
        print(f"  {action}: {count}")
    print()
    print("### By task")
    for task, count in sorted(by_task.items()):
        print(f"  {task}: {count}")


def cmd_diff(args):
    """Show git changes as Forge-ready output for the LLM to review and record.

    This is a LOW-FRICTION alternative to manual `record`:
    1. Run `changes diff {project} {task_id}` — shows git diff formatted for LLM
    2. LLM reviews, adds reasoning_trace and decision_ids
    3. LLM calls `changes record` with enriched data

    This solves the friction problem: instead of making the LLM remember to
    record changes, the workflow explicitly asks "what changed?" at task completion.
    """
    import subprocess

    task_id = args.task_id

    # Get staged + unstaged changes
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True, text=True, encoding="utf-8"
        )
        diff_stat = result.stdout.strip()
    except FileNotFoundError:
        print("WARNING: git not available. Use manual `record` instead.", file=sys.stderr)
        return

    if not diff_stat:
        # Try staged only
        result = subprocess.run(
            ["git", "diff", "--stat", "--cached"],
            capture_output=True, text=True, encoding="utf-8"
        )
        diff_stat = result.stdout.strip()

    if not diff_stat:
        print("No git changes detected. Nothing to record.")
        return

    # Parse diff stat into file entries
    print(f"## Git changes for task {task_id}")
    print()
    print(f"```")
    print(diff_stat)
    print(f"```")
    print()

    # Parse individual files from diff --numstat
    result = subprocess.run(
        ["git", "diff", "--numstat", "HEAD"],
        capture_output=True, text=True, encoding="utf-8"
    )
    if not result.stdout.strip():
        result = subprocess.run(
            ["git", "diff", "--numstat", "--cached"],
            capture_output=True, text=True, encoding="utf-8"
        )

    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            added, removed, filepath = parts
            added = int(added) if added != "-" else 0
            removed = int(removed) if removed != "-" else 0

            # Detect action
            action = "edit"
            check_new = subprocess.run(
                ["git", "diff", "--diff-filter=A", "--name-only", "HEAD", "--", filepath],
                capture_output=True, text=True, encoding="utf-8"
            )
            if filepath in check_new.stdout:
                action = "create"

            entries.append({
                "task_id": task_id,
                "file": filepath,
                "action": action,
                "summary": f"(add reasoning: what and why)",
                "lines_added": added,
                "lines_removed": removed,
            })

    if entries:
        print("Suggested change records (add reasoning_trace and decision_ids):")
        print()
        print("```json")
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        print("```")
        print()
        print("Record with:")
        print(f"  python -m core.changes record {args.project} --data '...'")


def cmd_contract(args):
    """Print contract spec."""
    print(render_contract("record", CONTRACTS["record"]))


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Changes -- change tracking with context")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("record", help="Record changes")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("diff", help="Show git changes for a task (low-friction recording)")
    p.add_argument("project")
    p.add_argument("task_id", help="Task ID to associate changes with")

    p = sub.add_parser("read", help="Read change log")
    p.add_argument("project")
    p.add_argument("--task", help="Filter by task_id")

    p = sub.add_parser("summary", help="Summary statistics")
    p.add_argument("project")

    sub.add_parser("contract", help="Print contract spec")

    args = parser.parse_args()

    commands = {
        "record": cmd_record,
        "diff": cmd_diff,
        "read": cmd_read,
        "summary": cmd_summary,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
