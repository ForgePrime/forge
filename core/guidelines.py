"""
Guidelines — project standards and conventions registry.

Stores coding standards, architectural conventions, and project-specific
rules that must be followed during task execution. Guidelines are scoped
(backend, frontend, database, general, etc.) and weighted (must/should/may)
to control how they're loaded into LLM context.

Guidelines are NOT versioned — deprecate old + create new instead of editing.

Usage:
    python -m core.guidelines <command> <project> [options]

Commands:
    add      {project} --data '{json}'         Add guidelines
    read     {project} [--scope X] [--status X] [--weight X]  Read guidelines
    update   {project} --data '{json}'         Update guideline status/content
    context  {project} --scopes "backend,db"   Formatted guidelines for LLM context
    scopes   {project}                         List unique scopes in project
    contract {name}                            Print contract spec
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

def guidelines_path(project: str) -> Path:
    return Path("forge_output") / project / "guidelines.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_or_create(project: str) -> dict:
    path = guidelines_path(project)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "project": project,
        "updated": now_iso(),
        "guidelines": [],
    }


def save_json(project: str, data: dict):
    path = guidelines_path(project)
    data["updated"] = now_iso()
    atomic_write_json(path, data)


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["title", "scope", "content"],
        "optional": ["rationale", "examples", "tags", "weight", "derived_from"],
        "enums": {
            "weight": {"must", "should", "may"},
        },
        "types": {
            "examples": list,
            "tags": list,
        },
        "invariant_texts": [
            "title: concise name for the guideline (e.g., 'Repository Pattern for data access')",
            "scope: area this applies to — open string, lowercase (e.g., 'backend', 'database', 'frontend', 'api', 'testing', 'general')",
            "content: the actual guideline — what to do and how",
            "rationale: WHY this guideline exists",
            "examples: concrete code or pattern examples",
            "tags: searchable keywords",
            "weight: 'must' (always loaded to LLM context), 'should' (loaded when <10, default), 'may' (only on explicit request)",
            "derived_from: objective ID this guideline was created because of (e.g., 'O-001'). "
            "Traceability — explains WHY this guideline exists. When objective status changes, review derived guidelines.",
        ],
        "example": [
            {
                "title": "Repository Pattern for data access",
                "scope": "backend",
                "content": "All database access goes through repository classes. No raw SQL in handlers or services. Repositories return domain objects, not ORM models.",
                "rationale": "Testability — repositories can be mocked. Single responsibility — data access isolated from business logic.",
                "examples": [
                    "class UserRepository:\n    def get_by_id(self, id: int) -> User: ...",
                    "# In handler: user = user_repo.get_by_id(id), NOT: user = db.query('SELECT...')",
                ],
                "tags": ["architecture", "data-access"],
                "weight": "must",
            },
            {
                "title": "SQL naming conventions",
                "scope": "database",
                "content": "snake_case for all identifiers. Plural table names (users, orders). Explicit column lists in SELECT — never SELECT *.",
                "weight": "should",
            },
        ],
    },
    "update": {
        "required": ["id"],
        "optional": ["title", "content", "status", "rationale",
                      "scope", "examples", "tags", "weight", "derived_from"],
        "enums": {
            "status": {"ACTIVE", "DEPRECATED"},
            "weight": {"must", "should", "may"},
        },
        "types": {
            "examples": list,
            "tags": list,
        },
        "invariant_texts": [
            "id: existing guideline ID (G-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "To change content significantly: deprecate old (status=DEPRECATED) and create new",
            "status=DEPRECATED: guideline no longer enforced, kept for history",
        ],
        "example": [
            {"id": "G-001", "status": "DEPRECATED"},
            {"id": "G-003", "weight": "must"},
        ],
    },
}


# -- Commands --

def cmd_add(args):
    """Add guidelines to the registry."""
    try:
        new_guidelines = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_guidelines, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["add"], new_guidelines)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    timestamp = now_iso()

    # Find next G-NNN ID
    existing_ids = [
        int(g["id"].split("-")[1]) for g in data.get("guidelines", [])
        if g.get("id", "").startswith("G-")
    ]
    next_id = max(existing_ids, default=0) + 1

    # Dedup by (scope, title) — normalized
    existing_keys = {
        (g.get("scope", "").lower().strip(), g.get("title", "").lower().strip())
        for g in data.get("guidelines", [])
    }

    added = []
    skipped = []
    for g in new_guidelines:
        scope = g["scope"].lower().strip()
        key = (scope, g["title"].lower().strip())
        if key in existing_keys:
            skipped.append(f"Duplicate: {g['title'][:50]}")
            continue

        guideline = {
            "id": f"G-{next_id:03d}",
            "title": g["title"],
            "scope": scope,
            "content": g["content"],
            "rationale": g.get("rationale", ""),
            "examples": g.get("examples", []),
            "tags": g.get("tags", []),
            "weight": g.get("weight", "should"),
            "derived_from": g.get("derived_from", ""),
            "status": "ACTIVE",
            "created": timestamp,
            "updated": timestamp,
        }

        data["guidelines"].append(guideline)
        existing_keys.add(key)
        added.append(guideline["id"])
        next_id += 1

    save_json(args.project, data)

    active_count = sum(1 for g in data["guidelines"] if g.get("status") == "ACTIVE")
    print(f"Guidelines saved: {args.project}")
    if added:
        print(f"  Added: {len(added)} ({', '.join(added)})")
    if skipped:
        print(f"  Skipped (duplicate): {len(skipped)}")
    print(f"  Total: {len(data['guidelines'])} | Active: {active_count}")


def cmd_read(args):
    """Read guidelines (optionally filtered)."""
    path = guidelines_path(args.project)
    if not path.exists():
        print(f"No guidelines for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    guidelines = data.get("guidelines", [])

    # Filter
    if args.scope:
        guidelines = [g for g in guidelines if g.get("scope") == args.scope.lower().strip()]
    if args.status:
        guidelines = [g for g in guidelines if g.get("status") == args.status]
    if args.weight:
        guidelines = [g for g in guidelines if g.get("weight") == args.weight]

    # Sort by ID
    guidelines.sort(key=lambda g: g.get("id", ""))

    # Render
    print(f"## Guidelines: {args.project}")
    filters = []
    if args.scope:
        filters.append(f"scope={args.scope}")
    if args.status:
        filters.append(f"status={args.status}")
    if args.weight:
        filters.append(f"weight={args.weight}")
    if filters:
        print(f"Filter: {', '.join(filters)}")
    print(f"Count: {len(guidelines)}")
    print()

    if not guidelines:
        print("(none)")
        return

    print("| ID | Scope | Weight | Title | Status |")
    print("|----|-------|--------|-------|--------|")
    for g in guidelines:
        title = g.get("title", "")[:50]
        print(f"| {g['id']} | {g.get('scope', '')} | {g.get('weight', '')} | {title} | {g.get('status', '')} |")

    # Show full content below table
    print()
    for g in guidelines:
        print(f"### {g['id']}: {g['title']}")
        derived = f" | **Derived from**: {g['derived_from']}" if g.get("derived_from") else ""
        print(f"**Scope**: {g['scope']} | **Weight**: {g['weight']} | **Status**: {g['status']}{derived}")
        print()
        print(g.get("content", ""))
        if g.get("rationale"):
            print()
            print(f"**Rationale**: {g['rationale']}")
        if g.get("examples"):
            print()
            print("**Examples**:")
            for ex in g["examples"]:
                print(f"  - {ex}")
        print()


def cmd_update(args):
    """Update guideline fields."""
    try:
        updates = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(updates, list):
        updates = [updates]

    errors = validate_contract(CONTRACTS["update"], updates)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    guidelines_by_id = {g["id"]: g for g in data.get("guidelines", [])}
    timestamp = now_iso()

    updated = []
    for u in updates:
        g_id = u["id"]
        if g_id not in guidelines_by_id:
            print(f"  WARNING: Guideline {g_id} not found, skipping", file=sys.stderr)
            continue

        g = guidelines_by_id[g_id]
        updatable = ["title", "content", "status", "rationale", "scope",
                      "examples", "tags", "weight", "derived_from"]
        for field in updatable:
            if field in u:
                if field == "scope":
                    g[field] = u[field].lower().strip()
                else:
                    g[field] = u[field]
        g["updated"] = timestamp
        updated.append(g_id)

    # Update in-place (preserve original list order)
    for g in data.get("guidelines", []):
        if g["id"] in guidelines_by_id:
            g.update(guidelines_by_id[g["id"]])
    save_json(args.project, data)

    active_count = sum(1 for g in data["guidelines"] if g.get("status") == "ACTIVE")
    print(f"Updated {len(updated)} guidelines: {args.project}")
    for g_id in updated:
        g = guidelines_by_id[g_id]
        print(f"  {g_id}: {g.get('title', '')[:40]} ({g.get('status', '')})")
    print(f"  Active: {active_count}")


def render_guidelines_context(active_guidelines: list, scopes: set, project: str = "",
                               global_guidelines: list = None) -> list:
    """Render guidelines as formatted Markdown lines for LLM context injection.

    Returns a list of strings (lines). Used by both `guidelines context` CLI
    and `pipeline context` to avoid duplicating rendering logic.

    global_guidelines bypass scope filtering — they are always included.
    """
    if global_guidelines is None:
        global_guidelines = []

    # Always include general scope for project guidelines
    scopes = set(scopes)
    scopes.add("general")

    # Global guidelines: always included (bypass scope filter)
    # Project guidelines: filtered by scope
    must = [g for g in global_guidelines if g.get("weight") == "must"]
    must += [g for g in active_guidelines if g.get("weight") == "must" and g.get("scope") in scopes]

    should = [g for g in global_guidelines if g.get("weight") == "should"]
    should += [g for g in active_guidelines if g.get("weight") == "should" and g.get("scope") in scopes]

    may = [g for g in global_guidelines if g.get("weight") == "may"]
    may += [g for g in active_guidelines if g.get("weight") == "may" and g.get("scope") in scopes]

    total = len(must) + len(should) + len(may)
    if total == 0:
        return []

    lines = [f"### Applicable Guidelines ({total})", ""]

    for g in must:
        lines.append(f"**{g['id']}** [{g['scope']}] {g['title']} _(MUST)_")
        lines.append(f"> {g['content']}")
        if g.get("examples"):
            for ex in g["examples"][:2]:
                lines.append(f"> Example: `{ex[:100]}`")
        lines.append("")

    show_full = total <= 10
    for g in should:
        lines.append(f"**{g['id']}** [{g['scope']}] {g['title']}")
        if show_full:
            lines.append(f"> {g['content']}")
        else:
            lines.append(f"> {g['content'][:120]}...")
        lines.append("")

    if may:
        lines.append(f"_Additional guidelines ({len(may)}):_")
        for g in may:
            lines.append(f"- {g['id']} [{g['scope']}] {g['title']}")
        lines.append("")

    if total > 10:
        proj_hint = f" `guidelines read {project} --scope X`" if project else " `guidelines read --scope X`"
        lines.append(f"_Showing {len(must)} must + {len(should)} should + {len(may)} may. Use{proj_hint} for full list._")

    return lines


def cmd_context(args):
    """Output formatted guidelines for LLM context injection."""
    # Load global guidelines (bypass scope filter) and project guidelines (scope-filtered)
    global_active = []
    if args.project != "_global":
        global_path = guidelines_path("_global")
        if global_path.exists():
            g_global = json.loads(global_path.read_text(encoding="utf-8"))
            global_active = [g for g in g_global.get("guidelines", []) if g.get("status") == "ACTIVE"]

    project_active = []
    path = guidelines_path(args.project)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        project_active = [g for g in data.get("guidelines", []) if g.get("status") == "ACTIVE"]

    if not global_active and not project_active:
        print("(no guidelines configured)")
        return

    requested_scopes = set()
    if args.scopes:
        requested_scopes = {s.strip().lower() for s in args.scopes.split(",")}

    lines = render_guidelines_context(project_active, requested_scopes, args.project,
                                       global_guidelines=global_active)
    for line in lines:
        print(line)


def cmd_scopes(args):
    """List unique scopes in the project."""
    path = guidelines_path(args.project)
    if not path.exists():
        print(f"No guidelines for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    guidelines = data.get("guidelines", [])

    scope_counts = {}
    for g in guidelines:
        if g.get("status") != "ACTIVE":
            continue
        scope = g.get("scope", "general")
        scope_counts[scope] = scope_counts.get(scope, 0) + 1

    if not scope_counts:
        print("No active guidelines.")
        return

    print(f"## Scopes: {args.project}")
    print()
    print("| Scope | Active Guidelines |")
    print("|-------|-------------------|")
    for scope, count in sorted(scope_counts.items()):
        print(f"| {scope} | {count} |")


def cmd_contract(args):
    """Print contract spec for a command."""
    if args.name not in CONTRACTS:
        print(f"ERROR: Unknown contract '{args.name}'", file=sys.stderr)
        print(f"Available: {', '.join(sorted(CONTRACTS.keys()))}", file=sys.stderr)
        sys.exit(1)
    print(render_contract(args.name, CONTRACTS[args.name]))


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Guidelines -- project standards registry")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Add guidelines")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="Read guidelines")
    p.add_argument("project")
    p.add_argument("--scope", help="Filter by scope")
    p.add_argument("--status", help="Filter by status")
    p.add_argument("--weight", help="Filter by weight")

    p = sub.add_parser("update", help="Update guidelines")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("context", help="Formatted guidelines for LLM context")
    p.add_argument("project")
    p.add_argument("--scopes", required=True, help="Comma-separated scopes")

    p = sub.add_parser("scopes", help="List unique scopes")
    p.add_argument("project")

    p = sub.add_parser("contract", help="Print contract spec")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "read": cmd_read,
        "update": cmd_update,
        "context": cmd_context,
        "scopes": cmd_scopes,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
