"""
Lessons — capture and reuse learnings from project execution.

Inspired by Compound Engineering Plugin's "Compound" phase:
"Each unit of engineering work should make subsequent units easier."

After a project completes (or a significant milestone), the LLM
reviews what happened and extracts reusable lessons:
- What went well
- What went wrong and how it was fixed
- Patterns discovered
- Decisions that should apply to future projects

Lessons are stored per-project but can be queried across projects.

Usage:
    python -m core.lessons <command> <project> [options]

Commands:
    add       {project} --data '{json}'     Add lessons learned
    read      {project}                      Read lessons for project
    read-all                                 Read lessons across all projects
    contract                                 Print contract spec
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

def lessons_path(project: str) -> Path:
    return Path("forge_output") / project / "lessons.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_or_create(project: str) -> dict:
    path = lessons_path(project)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "project": project,
        "updated": now_iso(),
        "lessons": [],
    }


def save_json(project: str, data: dict):
    path = lessons_path(project)
    data["updated"] = now_iso()
    atomic_write_json(path, data)


# -- Contract --

CONTRACTS = {
    "add": {
        "required": ["category", "title", "detail"],
        "optional": ["task_id", "decision_ids", "severity", "applies_to", "tags"],
        "enums": {
            "category": {
                "pattern-discovered",   # Reusable pattern found
                "mistake-avoided",      # What NOT to do
                "decision-validated",   # A decision proved correct
                "decision-reversed",    # A decision proved wrong
                "tool-insight",         # Better way to use a tool/library
                "architecture-lesson",  # Structural insight
                "process-improvement",  # Better workflow
                "market-insight",       # Business/market pattern discovered
            },
            "severity": {"critical", "important", "minor"},
        },
        "types": {
            "decision_ids": list,
            "tags": list,
        },
        "invariant_texts": [
            "title: concise, actionable (e.g. 'Always validate JWT audience field')",
            "detail: explain WHY this matters, not just WHAT happened",
            "applies_to: describe when this lesson is relevant (e.g. 'any API with auth')",
            "tags: searchable keywords for future retrieval",
        ],
        "example": [
            {
                "category": "mistake-avoided",
                "title": "Always validate JWT audience field",
                "detail": "We initially skipped audience validation. In testing, this allowed tokens from other services to access our API. Adding aud check caught this before production.",
                "task_id": "T-003",
                "decision_ids": ["D-001"],
                "severity": "critical",
                "applies_to": "Any API using JWT authentication",
                "tags": ["jwt", "security", "validation"],
            },
            {
                "category": "pattern-discovered",
                "title": "Use middleware chain over per-route guards",
                "detail": "Per-route auth guards led to 3 routes without auth. Middleware chain applies auth by default, explicit opt-out for public routes. Safer and less code.",
                "task_id": "T-004",
                "severity": "important",
                "applies_to": "Express/Fastify route-based APIs",
                "tags": ["middleware", "express", "auth"],
            },
        ],
    },
}


# -- Commands --

def cmd_add(args):
    """Add lessons learned."""
    try:
        new_lessons = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_lessons, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["add"], new_lessons)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    timestamp = now_iso()

    existing_ids = [
        int(l["id"].split("-")[1]) for l in data.get("lessons", [])
        if l.get("id", "").startswith("L-")
    ]
    next_id = max(existing_ids, default=0) + 1

    added = []
    for l in new_lessons:
        lesson = {
            "id": f"L-{next_id:03d}",
            "category": l["category"],
            "title": l["title"],
            "detail": l["detail"],
            "task_id": l.get("task_id", ""),
            "decision_ids": l.get("decision_ids", []),
            "severity": l.get("severity", "important"),
            "applies_to": l.get("applies_to", ""),
            "tags": l.get("tags", []),
            "project": args.project,
            "timestamp": timestamp,
        }
        data["lessons"].append(lesson)
        added.append(lesson["id"])
        next_id += 1

    save_json(args.project, data)

    print(f"Lessons recorded: {args.project}")
    print(f"  Added: {len(added)} ({', '.join(added)})")
    print(f"  Total: {len(data['lessons'])}")


def cmd_read(args):
    """Read lessons for a project."""
    path = lessons_path(args.project)
    if not path.exists():
        print(f"No lessons recorded for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    lessons = data.get("lessons", [])

    print(f"## Lessons: {args.project}")
    print(f"Count: {len(lessons)}")
    print()

    if not lessons:
        print("(none)")
        return

    for l in lessons:
        severity_icon = {"critical": "!!!", "important": " ! ", "minor": "   "}.get(l.get("severity", ""), "   ")
        print(f"### {l['id']} [{severity_icon}] {l['title']}")
        print(f"Category: {l['category']} | Applies to: {l.get('applies_to', '(general)')}")
        print(f"{l['detail']}")
        if l.get("tags"):
            print(f"Tags: {', '.join(l['tags'])}")
        print()


def cmd_read_all(args):
    """Read lessons across all projects."""
    output_dir = Path("forge_output")
    if not output_dir.exists():
        print("No projects found.")
        return

    all_lessons = []
    for project_dir in sorted(output_dir.iterdir()):
        if project_dir.is_dir():
            lpath = project_dir / "lessons.json"
            if lpath.exists():
                data = json.loads(lpath.read_text(encoding="utf-8"))
                all_lessons.extend(data.get("lessons", []))

    if not all_lessons:
        print("No lessons recorded across any project.")
        return

    # Sort by severity then timestamp
    severity_order = {"critical": 0, "important": 1, "minor": 2}
    all_lessons.sort(key=lambda l: (severity_order.get(l.get("severity", "minor"), 2), l.get("timestamp", "")))

    print(f"## All Lessons ({len(all_lessons)} total)")
    print()

    for l in all_lessons:
        severity_icon = {"critical": "!!!", "important": " ! ", "minor": "   "}.get(l.get("severity", ""), "   ")
        print(f"### {l['id']} [{severity_icon}] {l['title']} (from: {l.get('project', '?')})")
        print(f"Category: {l['category']} | Applies to: {l.get('applies_to', '(general)')}")
        print(f"{l['detail']}")
        if l.get("tags"):
            print(f"Tags: {', '.join(l['tags'])}")
        print()


def cmd_contract(args):
    """Print contract spec."""
    print(render_contract("add", CONTRACTS["add"]))


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Lessons -- compound learning from project execution")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Add lessons learned")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="Read lessons for project")
    p.add_argument("project")

    sub.add_parser("read-all", help="Read lessons across all projects")

    sub.add_parser("contract", help="Print contract spec")

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "read": cmd_read,
        "read-all": cmd_read_all,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
