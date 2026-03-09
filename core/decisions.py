"""
Decisions — centralized decision log with provenance tracking.

Evolved from Skill_v1's forge_decisions.py. Key differences:
- Domain-agnostic: decisions about code, architecture, dependencies — not just fields
- Richer provenance: who decided (human/claude), confidence, alternatives considered
- Linked to tasks: every decision belongs to a task in the pipeline

Every decision records:
- WHAT: the issue and recommendation
- WHO: human or AI, with confidence level
- WHY: reasoning and alternatives considered
- WHEN: timestamp
- STATUS: OPEN (needs review), CLOSED (resolved), DEFERRED (later)

Usage:
    python -m core.decisions <command> <project> [options]

Commands:
    add      {project} --data '{json}'         Add decisions
    read     {project} [--status X] [--task X]  Read decisions
    update   {project} --data '{json}'          Update decision statuses
    contract {name}                             Print contract spec
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import contracts from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract, atomic_write_json

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


# -- Paths --

def decisions_path(project: str) -> Path:
    return Path("forge_output") / project / "decisions.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_or_create(project: str) -> dict:
    path = decisions_path(project)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "project": project,
        "updated": now_iso(),
        "decisions": [],
        "open_count": 0,
    }


def save_json(project: str, data: dict):
    path = decisions_path(project)
    data["updated"] = now_iso()
    data["open_count"] = sum(1 for d in data.get("decisions", []) if d.get("status") == "OPEN")
    atomic_write_json(path, data)


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["task_id", "type", "issue", "recommendation"],
        "optional": ["reasoning", "alternatives", "confidence", "status",
                      "decided_by", "file", "scope"],
        "enums": {
            "type": {"architecture", "implementation", "dependency", "security",
                     "performance", "testing", "naming", "convention", "constraint",
                     "business", "strategy", "other"},
            "confidence": {"HIGH", "MEDIUM", "LOW"},
            "status": {"OPEN", "CLOSED", "DEFERRED"},
            "decided_by": {"claude", "user", "imported"},
        },
        "types": {
            "alternatives": list,
        },
        "invariant_texts": [
            "task_id must reference an existing task in the pipeline",
            "OPEN decisions need human review before proceeding",
            "CLOSED decisions with decided_by='user' are Priority 0 overrides",
        ],
        "example": [
            {
                "task_id": "T-003",
                "type": "architecture",
                "issue": "JWT signing algorithm: RS256 vs HS256",
                "recommendation": "RS256",
                "reasoning": "Allows key rotation without redeploying all services",
                "alternatives": ["HS256 (simpler but shared secret)", "EdDSA (faster but less support)"],
                "confidence": "HIGH",
                "decided_by": "claude",
            },
            {
                "task_id": "T-005",
                "type": "implementation",
                "issue": "Error handling pattern for API routes",
                "recommendation": "Centralized error middleware with typed error classes",
                "reasoning": "Consistent error responses, single point of logging",
                "confidence": "MEDIUM",
                "status": "OPEN",
                "decided_by": "claude",
            },
        ],
    },
    "update": {
        "required": ["id", "status"],
        "optional": ["action", "override_value", "override_reason"],
        "enums": {
            "status": {"CLOSED", "DEFERRED"},
            "action": {"accept", "override", "defer"},
        },
        "invariant_texts": [
            "accept: agree with recommendation, close decision",
            "override: provide override_value and override_reason",
            "defer: mark for later review",
        ],
        "example": [
            {"id": "D-001", "status": "CLOSED", "action": "accept"},
            {"id": "D-003", "status": "CLOSED", "action": "override",
             "override_value": "HS256", "override_reason": "Simpler for MVP, will migrate to RS256 later"},
            {"id": "D-005", "status": "DEFERRED", "action": "defer"},
        ],
    },
}


# -- Commands --

def cmd_add(args):
    """Add decisions to the log."""
    try:
        new_decisions = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_decisions, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["add"], new_decisions)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    # Cross-validate: check task_ids exist in pipeline
    tracker_file = Path("forge_output") / args.project / "tracker.json"
    if tracker_file.exists():
        tracker = json.loads(tracker_file.read_text(encoding="utf-8"))
        valid_task_ids = {t["id"] for t in tracker.get("tasks", [])}
        # Special task IDs used by skills for pre-task decisions
        special_ids = {"PLANNING", "ONBOARDING", "REVIEW", "DISCOVERY"}
        # Also allow idea IDs (I-NNN) as task_id for exploration decisions
        ideas_file = Path("forge_output") / args.project / "ideas.json"
        idea_ids = set()
        if ideas_file.exists():
            ideas_data = json.loads(ideas_file.read_text(encoding="utf-8"))
            idea_ids = {i["id"] for i in ideas_data.get("ideas", [])}
        for d in new_decisions:
            tid = d.get("task_id", "")
            if tid and tid not in valid_task_ids and tid not in special_ids and tid not in idea_ids:
                print(f"WARNING: task_id '{tid}' not found in pipeline or ideas. Decision will be saved but may be orphaned.", file=sys.stderr)

    data = load_or_create(args.project)
    timestamp = now_iso()

    # Find next D-NNN ID
    existing_ids = [
        int(d["id"].split("-")[1]) for d in data.get("decisions", [])
        if d.get("id", "").startswith("D-")
    ]
    next_id = max(existing_ids, default=0) + 1

    # Dedup by (task_id, type, issue) composite key
    existing_keys = {
        (d.get("task_id"), d.get("type"), d.get("issue"))
        for d in data.get("decisions", [])
    }

    added = []
    skipped = []
    for d in new_decisions:
        key = (d.get("task_id"), d.get("type"), d.get("issue"))
        if key in existing_keys:
            skipped.append(f"Duplicate: {d.get('issue', '')[:50]}")
            continue

        decision = {
            "id": f"D-{next_id:03d}",
            "task_id": d["task_id"],
            "type": d["type"],
            "issue": d["issue"],
            "recommendation": d["recommendation"],
            "reasoning": d.get("reasoning", ""),
            "alternatives": d.get("alternatives", []),
            "confidence": d.get("confidence", "MEDIUM"),
            "status": d.get("status", "OPEN"),
            "decided_by": d.get("decided_by", "claude"),
            "file": d.get("file", ""),
            "scope": d.get("scope", ""),
            "timestamp": timestamp,
        }

        data["decisions"].append(decision)
        existing_keys.add(key)
        added.append(decision["id"])
        next_id += 1

    save_json(args.project, data)

    print(f"Decisions saved: {args.project}")
    if added:
        print(f"  Added: {len(added)} ({', '.join(added)})")
    if skipped:
        print(f"  Skipped (duplicate): {len(skipped)}")
    print(f"  Total: {len(data['decisions'])} | Open: {data['open_count']}")


def cmd_read(args):
    """Read decisions (optionally filtered)."""
    path = decisions_path(args.project)
    if not path.exists():
        print(f"No decisions for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    decisions = data.get("decisions", [])

    # Filter
    if args.status:
        decisions = [d for d in decisions if d.get("status") == args.status]
    if args.task:
        decisions = [d for d in decisions if d.get("task_id") == args.task]

    # Sort by ID
    decisions.sort(key=lambda d: d.get("id", ""))

    # Render as Markdown table
    print(f"## Decisions: {args.project}")
    filters = []
    if args.status:
        filters.append(f"status={args.status}")
    if args.task:
        filters.append(f"task={args.task}")
    if filters:
        print(f"Filter: {', '.join(filters)}")
    print(f"Count: {len(decisions)}")
    print()

    if not decisions:
        print("(none)")
        return

    print("| ID | Task | Type | Issue | Recommendation | Status | By | Conf |")
    print("|----|------|------|-------|----------------|--------|----|------|")
    for d in decisions:
        issue = d.get("issue", "")[:40]
        rec = d.get("recommendation", "")[:30]
        print(f"| {d['id']} | {d.get('task_id', '')} | {d.get('type', '')} | {issue} | {rec} | {d.get('status', '')} | {d.get('decided_by', '')} | {d.get('confidence', '')} |")


def cmd_update(args):
    """Update decision statuses."""
    try:
        updates = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["update"], updates)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    decisions_by_id = {d["id"]: d for d in data.get("decisions", [])}
    timestamp = now_iso()

    updated = []
    for u in updates:
        d_id = u["id"]
        if d_id not in decisions_by_id:
            print(f"  WARNING: Decision {d_id} not found, skipping")
            continue

        d = decisions_by_id[d_id]
        d["status"] = u["status"]
        if "action" in u:
            d["action"] = u["action"]
        if "override_value" in u:
            d["override_value"] = u["override_value"]
        if "override_reason" in u:
            d["override_reason"] = u["override_reason"]
        d["updated"] = timestamp
        updated.append(d_id)

    data["decisions"] = list(decisions_by_id.values())
    save_json(args.project, data)

    print(f"Updated {len(updated)} decisions: {args.project}")
    for d_id in updated:
        d = decisions_by_id[d_id]
        print(f"  {d_id}: {d.get('status')} ({d.get('action', '')})")
    print(f"  Open: {data['open_count']}")


def cmd_contract(args):
    """Print contract spec for a command."""
    if args.name not in CONTRACTS:
        print(f"ERROR: Unknown contract '{args.name}'", file=sys.stderr)
        print(f"Available: {', '.join(sorted(CONTRACTS.keys()))}", file=sys.stderr)
        sys.exit(1)
    print(render_contract(args.name, CONTRACTS[args.name]))


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Decisions -- decision log with provenance")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Add decisions")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="Read decisions")
    p.add_argument("project")
    p.add_argument("--status", help="Filter by status")
    p.add_argument("--task", help="Filter by task_id")

    p = sub.add_parser("update", help="Update decision statuses")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("contract", help="Print contract spec")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "read": cmd_read,
        "update": cmd_update,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
