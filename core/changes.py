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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract
from storage import JSONFileStorage, now_iso

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


# -- Storage --

def load_or_create(project: str, storage=None) -> dict:
    if storage is None:
        storage = JSONFileStorage()
    return storage.load_data(project, 'changes')


def save_json(project: str, data: dict, storage=None):
    if storage is None:
        storage = JSONFileStorage()
    storage.save_data(project, 'changes', data)


# -- Contract --

CONTRACTS = {
    "record": {
        "required": ["task_id", "file", "action", "summary"],
        "optional": ["reasoning_trace", "decision_ids", "lines_added",
                      "lines_removed", "group_id", "guidelines_checked"],
        "enums": {
            "action": {"create", "edit", "delete", "rename", "move"},
        },
        "types": {
            "reasoning_trace": list,
            "decision_ids": list,
            "lines_added": int,
            "lines_removed": int,
            "guidelines_checked": list,
        },
        "invariant_texts": [
            "task_id must reference an existing task in the pipeline",
            "file must be a relative path from project root",
            "reasoning_trace: array of {step, detail} objects explaining the change",
            "decision_ids: list of D-NNN IDs that led to this change",
            "group_id: links related changes across files (e.g. a refactor touching 5 files)",
            "guidelines_checked: list of G-NNN IDs that were verified during this change",
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
    storage = JSONFileStorage()
    valid_task_ids = set()
    valid_decision_ids = set()
    if storage.exists(args.project, 'tracker'):
        tracker = storage.load_data(args.project, 'tracker')
        valid_task_ids = {t["id"] for t in tracker.get("tasks", [])}
    if storage.exists(args.project, 'decisions'):
        dec_data = storage.load_data(args.project, 'decisions')
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
            "guidelines_checked": c.get("guidelines_checked", []),
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
    storage = JSONFileStorage()
    if not storage.exists(args.project, 'changes'):
        print(f"No changes recorded for '{args.project}' yet.")
        return

    data = storage.load_data(args.project, 'changes')
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
    storage = JSONFileStorage()
    if not storage.exists(args.project, 'changes'):
        print(f"No changes recorded for '{args.project}' yet.")
        return

    data = storage.load_data(args.project, 'changes')
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


def cmd_auto(args):
    """Auto-detect git changes and record them in one step.

    Combines `diff` + `record` into a single command. The LLM provides
    a reasoning string and optional decision_ids/guidelines_checked —
    Python handles the git parsing and record creation.
    """
    import subprocess

    task_id = args.task_id
    reasoning = args.reasoning or ""
    decision_ids = [d.strip() for d in args.decision_ids.split(",") if d.strip()] if args.decision_ids else []
    guidelines = [g.strip() for g in args.guidelines.split(",") if g.strip()] if args.guidelines else []

    # Get changes from git
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", "HEAD"],
            capture_output=True, text=True, encoding="utf-8"
        )
        numstat = result.stdout.strip()
    except FileNotFoundError:
        print("ERROR: git not available. Use `changes record` instead.", file=sys.stderr)
        sys.exit(1)

    if not numstat:
        # Try staged only
        result = subprocess.run(
            ["git", "diff", "--numstat", "--cached"],
            capture_output=True, text=True, encoding="utf-8"
        )
        numstat = result.stdout.strip()

    if not numstat:
        print("No git changes detected. Nothing to record.")
        return

    # Parse numstat into change records
    data = load_or_create(args.project)
    timestamp = now_iso()

    existing_ids = [
        int(c["id"].split("-")[1]) for c in data.get("changes", [])
        if c.get("id", "").startswith("C-")
    ]
    next_id = max(existing_ids, default=0) + 1

    # Dedup: skip files already recorded for this task (idempotency)
    existing_files = {c["file"] for c in data.get("changes", [])
                      if c.get("task_id") == task_id}

    recorded = []
    skipped = 0
    for line in numstat.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, filepath = parts
        added = int(added) if added != "-" else 0
        removed = int(removed) if removed != "-" else 0

        # Skip if already recorded for this task (idempotency)
        if filepath in existing_files:
            skipped += 1
            continue

        # Detect action
        action = "edit"
        if removed == 0 and added > 0:
            check = subprocess.run(
                ["git", "diff", "--diff-filter=A", "--name-only", "HEAD", "--", filepath],
                capture_output=True, text=True, encoding="utf-8"
            )
            if filepath in check.stdout:
                action = "create"
        elif added == 0 and removed > 0:
            check = subprocess.run(
                ["git", "diff", "--diff-filter=D", "--name-only", "HEAD", "--", filepath],
                capture_output=True, text=True, encoding="utf-8"
            )
            if filepath in check.stdout:
                action = "delete"

        change = {
            "id": f"C-{next_id:03d}",
            "task_id": task_id,
            "file": filepath,
            "action": action,
            "summary": reasoning,
            "reasoning_trace": [{"step": "auto", "detail": reasoning}] if reasoning else [],
            "decision_ids": decision_ids,
            "lines_added": added,
            "lines_removed": removed,
            "group_id": task_id,
            "guidelines_checked": guidelines,
            "timestamp": timestamp,
        }
        data["changes"].append(change)
        recorded.append(f"{change['id']} ({action} {filepath})")
        next_id += 1

    save_json(args.project, data)

    if not recorded and skipped:
        print(f"No new changes to record for {task_id} ({skipped} already recorded).")
        return

    print(f"Changes auto-recorded: {args.project}")
    print(f"  Task: {task_id}")
    print(f"  Recorded: {len(recorded)}")
    if skipped:
        print(f"  Skipped (already recorded): {skipped}")
    for r in recorded:
        print(f"    {r}")
    if decision_ids:
        print(f"  Decisions: {', '.join(decision_ids)}")
    if guidelines:
        print(f"  Guidelines checked: {', '.join(guidelines)}")


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

    p = sub.add_parser("auto", help="Auto-detect git changes and record (one-step)")
    p.add_argument("project")
    p.add_argument("task_id", help="Task ID to associate changes with")
    p.add_argument("--reasoning", help="Why these changes were made")
    p.add_argument("--decision_ids", help="Comma-separated D-NNN IDs")
    p.add_argument("--guidelines", help="Comma-separated G-NNN IDs checked")

    sub.add_parser("contract", help="Print contract spec")

    args = parser.parse_args()

    commands = {
        "record": cmd_record,
        "auto": cmd_auto,
        "diff": cmd_diff,
        "read": cmd_read,
        "summary": cmd_summary,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
