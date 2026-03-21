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
    import   {project} --source {other}        Import guidelines from another project
    contract {name}                            Print contract spec
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from entity_base import EntityModule, make_cli
from storage import JSONFileStorage, now_iso


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


# -- Module --

class Guidelines(EntityModule):
    entity_type = "guidelines"
    list_key = "guidelines"
    id_prefix = "G"
    display_name = "Guidelines"
    contracts = CONTRACTS
    dedup_keys = ("scope", "title")

    def build_entity(self, input_item, entity_id, timestamp, args):
        return {
            "id": entity_id,
            "title": input_item["title"],
            "scope": input_item["scope"].lower().strip(),
            "content": input_item["content"],
            "rationale": input_item.get("rationale", ""),
            "examples": input_item.get("examples", []),
            "tags": input_item.get("tags", []),
            "weight": input_item.get("weight", "should"),
            "derived_from": input_item.get("derived_from", ""),
            "status": "ACTIVE",
            "created": timestamp,
            "updated": timestamp,
        }

    def print_add_summary(self, project, data, added, skipped):
        active_count = sum(1 for g in self.items(data) if g.get("status") == "ACTIVE")
        print(f"Guidelines saved: {project}")
        if added:
            print(f"  Added: {len(added)} ({', '.join(added)})")
        if skipped:
            print(f"  Skipped (duplicate): {len(skipped)}")
        print(f"  Total: {len(self.items(data))} | Active: {active_count}")

    def apply_filters(self, items, args):
        if getattr(args, "scope", None):
            items = [g for g in items if g.get("scope") == args.scope.lower().strip()]
        if getattr(args, "status", None):
            items = [g for g in items if g.get("status") == args.status]
        if getattr(args, "weight", None):
            items = [g for g in items if g.get("weight") == args.weight]
        return items

    def render_list(self, items, args):
        print(f"## Guidelines: {args.project}")
        filters = []
        if getattr(args, "scope", None):
            filters.append(f"scope={args.scope}")
        if getattr(args, "status", None):
            filters.append(f"status={args.status}")
        if getattr(args, "weight", None):
            filters.append(f"weight={args.weight}")
        if filters:
            print(f"Filter: {', '.join(filters)}")
        print(f"Count: {len(items)}")
        print()

        if not items:
            print("(none)")
            return

        print("| ID | Scope | Weight | Title | Status |")
        print("|----|-------|--------|-------|--------|")
        for g in items:
            title = g.get("title", "")[:50]
            print(f"| {g['id']} | {g.get('scope', '')} | {g.get('weight', '')} | {title} | {g.get('status', '')} |")

        # Show full content below table
        print()
        for g in items:
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

    def apply_update(self, item, update, timestamp):
        updatable = ["title", "scope", "content", "rationale",
                      "examples", "tags", "weight", "status", "derived_from"]
        for field in updatable:
            if field in update:
                if field == "scope":
                    item[field] = update[field].lower().strip()
                else:
                    item[field] = update[field]
        item["updated"] = timestamp


_mod = Guidelines()

# Public API used by other modules
load_or_create = _mod.load
save_json = _mod.save

# Test compatibility exports
cmd_add = _mod.cmd_add
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update


# -- Custom commands (standalone) --

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
    storage = JSONFileStorage()

    # Load global guidelines (bypass scope filter) and project guidelines (scope-filtered)
    global_active = []
    if args.project != "_global":
        g_global = storage.load_global('guidelines')
        global_active = [g for g in g_global.get("guidelines", []) if g.get("status") == "ACTIVE"]

    project_active = []
    if storage.exists(args.project, 'guidelines'):
        data = storage.load_data(args.project, 'guidelines')
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
    storage = JSONFileStorage()
    if not storage.exists(args.project, 'guidelines'):
        print(f"No guidelines for '{args.project}' yet.")
        return

    data = storage.load_data(args.project, 'guidelines')
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


def cmd_import(args):
    """Import guidelines from another project into this one."""
    storage = JSONFileStorage()
    if not storage.exists(args.source, 'guidelines'):
        print(f"ERROR: No guidelines found in project '{args.source}'", file=sys.stderr)
        sys.exit(1)

    source_data = storage.load_data(args.source, 'guidelines')
    source_guidelines = [g for g in source_data.get("guidelines", []) if g.get("status") == "ACTIVE"]

    if not source_guidelines:
        print(f"No active guidelines in '{args.source}'.")
        return

    # Filter by scope if specified
    if args.scope:
        scope_filter = args.scope.lower()
        source_guidelines = [g for g in source_guidelines if g.get("scope", "").lower() == scope_filter]
        if not source_guidelines:
            print(f"No active guidelines with scope '{args.scope}' in '{args.source}'.")
            return

    # Load target project
    target_data = load_or_create(args.project)
    target_titles = {g.get("title", "").lower() for g in target_data.get("guidelines", [])}

    # Generate next ID
    existing_ids = [
        int(g["id"].split("-")[1]) for g in target_data.get("guidelines", [])
        if g.get("id", "").startswith("G-")
    ]
    next_id = max(existing_ids, default=0) + 1

    imported = []
    skipped = []
    timestamp = now_iso()

    for g in source_guidelines:
        if g.get("title", "").lower() in target_titles:
            skipped.append(g.get("id", "?"))
            continue

        new_guideline = {
            "id": f"G-{next_id:03d}",
            "title": g["title"],
            "scope": g.get("scope", "general"),
            "content": g.get("content", ""),
            "rationale": g.get("rationale", "") + f" (imported from {args.source}/{g.get('id', '?')})",
            "weight": g.get("weight", "should"),
            "tags": g.get("tags", []),
            "examples": g.get("examples", []),
            "status": "ACTIVE",
            "imported_from": f"{args.source}/{g.get('id', '?')}",
            "timestamp": timestamp,
        }
        target_data["guidelines"].append(new_guideline)
        imported.append(new_guideline["id"])
        next_id += 1

    if imported:
        save_json(args.project, target_data)

    print(f"Guidelines imported: {args.source} → {args.project}")
    print(f"  Imported: {len(imported)} ({', '.join(imported)})")
    if skipped:
        print(f"  Skipped (duplicate titles): {len(skipped)} ({', '.join(skipped)})")
    print(f"  Total in {args.project}: {len(target_data['guidelines'])}")


# -- CLI --

def _setup_extra_parsers(sub):
    # Add extra args to the 'read' parser — we need to get it from the subparsers
    # Since make_cli creates 'read' before calling this, we access it via choices
    read_parser = sub.choices.get("read")
    if read_parser:
        read_parser.add_argument("--scope", help="Filter by scope")
        read_parser.add_argument("--status", choices=["ACTIVE", "DEPRECATED"],
                                  help="Filter by status")
        read_parser.add_argument("--weight", choices=["must", "should", "may"],
                                  help="Filter by weight")

    p = sub.add_parser("context", help="Formatted guidelines for LLM context")
    p.add_argument("project")
    p.add_argument("--scopes", required=True, help="Comma-separated scopes")

    p = sub.add_parser("scopes", help="List unique scopes")
    p.add_argument("project")

    p = sub.add_parser("import", help="Import guidelines from another project")
    p.add_argument("project", help="Target project")
    p.add_argument("--source", required=True, help="Source project to import from")
    p.add_argument("--scope", help="Only import guidelines with this scope")


def main():
    make_cli(
        _mod,
        extra_commands={
            "context": cmd_context,
            "scopes": cmd_scopes,
            "import": cmd_import,
        },
        setup_extra_parsers=_setup_extra_parsers,
        description="Forge Guidelines -- project standards registry",
    )


if __name__ == "__main__":
    main()
