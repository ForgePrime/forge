"""
Research — structured analysis output (R-NNN).

Captures structured summaries of research/discovery work, linking
full analysis files (research/*.md) to objectives, ideas, and decisions.
Supports CRUD, entity-aware context loading, and status lifecycle.

Usage:
    python -m core.research <command> <project> [options]

Commands:
    add          {project} --data '{json}'                           Create research objects
    read         {project} [--status X] [--category X] [--entity X]  List/filter
    show         {project} {research_id}                             Full details
    update       {project} --data '{json}'                           Update status/fields
    context      {project} --entity {O-001|I-001}                    Research for LLM context
    contract     {name}                                              Print contract spec
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract
from storage import JSONFileStorage, load_json_data, now_iso

from _compat import configure_encoding
configure_encoding()


# -- Storage --

def load_or_create(project: str, storage=None) -> dict:
    if storage is None:
        storage = JSONFileStorage()
    return storage.load_data(project, 'research')


def save_json(project: str, data: dict, storage=None):
    if storage is None:
        storage = JSONFileStorage()
    storage.save_data(project, 'research', data)


# -- Constants --

VALID_CATEGORIES = {
    "architecture", "domain", "feasibility", "risk", "business", "technical",
}

VALID_STATUSES = {"DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"}

VALID_TRANSITIONS = {
    "DRAFT": {"ACTIVE", "ARCHIVED"},
    "ACTIVE": {"SUPERSEDED", "ARCHIVED"},
    "SUPERSEDED": {"ARCHIVED"},
    "ARCHIVED": set(),
}

VALID_LINKED_ENTITY_TYPES = {"objective", "idea"}


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["title", "topic", "category", "summary"],
        "optional": [
            "linked_entity_type", "linked_entity_id", "linked_idea_id",
            "skill", "file_path", "content", "key_findings", "decision_ids",
            "scopes", "tags", "created_by",
        ],
        "enums": {
            "category": VALID_CATEGORIES,
            "linked_entity_type": VALID_LINKED_ENTITY_TYPES,
        },
        "types": {
            "key_findings": list,
            "decision_ids": list,
            "scopes": list,
            "tags": list,
        },
        "invariant_texts": [
            "title: concise title for the research (e.g., 'Caching Layer Architecture Analysis')",
            "topic: the question being researched (e.g., 'Redis vs in-memory caching for API')",
            "category: one of architecture, domain, feasibility, risk, business, technical",
            "summary: 1-3 sentence summary of key findings and recommendation",
            "linked_entity_type: 'objective' or 'idea' (omit for standalone research)",
            "linked_entity_id: O-NNN or I-NNN ID of linked entity",
            "linked_idea_id: I-NNN — additional idea link when primary entity is an objective",
            "skill: which deep-* skill produced this (e.g., 'deep-explore')",
            "file_path: path to research markdown file relative to project dir (e.g., 'research/deep-explore-caching.md'). Auto-generated from skill+title if content is provided and file_path is omitted.",
            "content: full markdown content for the research file. When provided, the file is written to file_path (or auto-generated path) by the core module. Use this instead of writing files directly.",
            "key_findings: list of bullet-point findings (strings)",
            "decision_ids: list of D-NNN IDs that originated from this research",
            "scopes: guideline scopes this research relates to (e.g., ['backend', 'performance'])",
            "tags: searchable keywords",
            "created_by: 'user' or 'claude' (default: 'claude')",
        ],
        "example": [
            {
                "title": "Caching Layer Architecture Analysis",
                "topic": "Redis vs in-memory caching for API endpoints",
                "category": "architecture",
                "summary": "Redis recommended for shared cache with pub/sub invalidation.",
                "linked_entity_type": "objective",
                "linked_entity_id": "O-001",
                "skill": "deep-explore",
                "file_path": "research/deep-explore-caching.md",
                "key_findings": [
                    "DB queries average 200ms, caching reduces to <10ms",
                    "Redis cluster supports horizontal scaling",
                ],
                "decision_ids": ["D-001", "D-002"],
                "scopes": ["backend", "performance"],
                "tags": ["redis", "caching"],
            },
        ],
    },
    "update": {
        "required": ["id"],
        "optional": [
            "title", "topic", "status", "category", "summary",
            "key_findings", "decision_ids", "file_path",
            "linked_idea_id", "scopes", "tags",
        ],
        "enums": {
            "status": VALID_STATUSES,
            "category": VALID_CATEGORIES,
        },
        "types": {
            "key_findings": list,
            "decision_ids": list,
            "scopes": list,
            "tags": list,
        },
        "invariant_texts": [
            "id: existing research ID (R-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "status transitions: DRAFT->ACTIVE, DRAFT->ARCHIVED, "
            "ACTIVE->SUPERSEDED, ACTIVE->ARCHIVED, SUPERSEDED->ARCHIVED",
            "decision_ids: replaces the full list (not append-merged)",
        ],
        "example": [
            {"id": "R-001", "status": "ACTIVE"},
            {"id": "R-002", "decision_ids": ["D-001", "D-002", "D-005"]},
        ],
    },
}


# -- Helpers --

def find_research(data: dict, research_id: str) -> dict | None:
    """Find research object by ID."""
    for r in data.get("research", []):
        if r["id"] == research_id:
            return r
    return None


def _next_id(data: dict) -> str:
    """Generate next R-NNN ID."""
    existing = [
        int(r["id"].split("-")[1]) for r in data.get("research", [])
        if r.get("id", "").startswith("R-")
    ]
    num = max(existing, default=0) + 1
    return f"R-{num:03d}"


# -- Commands --

def cmd_add(args):
    """Create research objects."""
    try:
        new_items = load_json_data(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_items, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["add"], new_items)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    timestamp = now_iso()

    # Dedup by (category, title) — normalized
    existing_keys = {
        (r.get("category", "").lower().strip(), r.get("title", "").lower().strip())
        for r in data.get("research", [])
    }

    added = []
    skipped = []
    for item in new_items:
        category = item["category"].lower().strip()
        key = (category, item["title"].lower().strip())
        if key in existing_keys:
            skipped.append(f"Duplicate: {item['title'][:50]}")
            continue

        r_id = _next_id(data)

        # Validate linked entity
        entity_type = item.get("linked_entity_type")
        entity_id = item.get("linked_entity_id")
        if entity_type and not entity_id:
            print(f"WARNING: linked_entity_type set but linked_entity_id missing for '{item['title']}'",
                  file=sys.stderr)
        if entity_id and not entity_type:
            print(f"WARNING: linked_entity_id set but linked_entity_type missing for '{item['title']}'",
                  file=sys.stderr)

        # Handle content → file writing
        content = item.get("content")
        file_path = item.get("file_path")
        if content and not file_path:
            # Auto-generate file_path from skill + title
            skill = item.get("skill", "research")
            slug = item["title"].lower()
            slug = slug.replace(" ", "-").replace(":", "")[:60]
            # Keep only safe chars
            slug = "".join(c for c in slug if c.isalnum() or c == "-")
            slug = slug.strip("-")
            file_path = f"research/{skill}-{slug}.md"

        if content and file_path:
            storage = JSONFileStorage()
            project_dir = storage.base_dir / args.project
            full_path = os.path.join(str(project_dir), file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Wrote research file: {file_path}")

        research = {
            "id": r_id,
            "title": item["title"],
            "topic": item["topic"],
            "status": "DRAFT",
            "category": category,
            "linked_entity_type": entity_type,
            "linked_entity_id": entity_id,
            "linked_idea_id": item.get("linked_idea_id"),
            "skill": item.get("skill"),
            "file_path": file_path,
            "summary": item["summary"],
            "key_findings": item.get("key_findings", []),
            "decision_ids": item.get("decision_ids", []),
            "scopes": item.get("scopes", []),
            "tags": item.get("tags", []),
            "created_at": timestamp,
            "updated_at": timestamp,
            "created_by": item.get("created_by", "claude"),
        }

        data["research"].append(research)
        existing_keys.add(key)
        added.append(r_id)

    save_json(args.project, data)

    print(f"Research saved: {args.project}")
    if added:
        print(f"  Added: {len(added)} ({', '.join(added)})")
    if skipped:
        print(f"  Skipped (duplicate): {len(skipped)}")
    print(f"  Total: {len(data['research'])}")


def cmd_read(args):
    """List/filter research objects."""
    storage = JSONFileStorage()
    if not storage.exists(args.project, 'research'):
        print(f"No research for '{args.project}' yet.")
        return

    data = storage.load_data(args.project, 'research')
    items = data.get("research", [])

    # Filter
    if args.status:
        items = [r for r in items if r.get("status") == args.status]
    if args.category:
        items = [r for r in items if r.get("category") == args.category.lower().strip()]
    if args.entity:
        entity_id = args.entity
        items = [r for r in items
                 if r.get("linked_entity_id") == entity_id
                 or r.get("linked_idea_id") == entity_id]

    # Sort by ID
    items.sort(key=lambda r: r.get("id", ""))

    # Render
    print(f"## Research: {args.project}")
    filters = []
    if args.status:
        filters.append(f"status={args.status}")
    if args.category:
        filters.append(f"category={args.category}")
    if args.entity:
        filters.append(f"entity={args.entity}")
    if filters:
        print(f"Filter: {', '.join(filters)}")
    print(f"Count: {len(items)}")
    print()

    if not items:
        print("(none)")
        return

    print("| ID | Category | Status | Entity | Title |")
    print("|----|----------|--------|--------|-------|")
    for r in items:
        title = r.get("title", "")[:40]
        entity = r.get("linked_entity_id") or "—"
        print(f"| {r['id']} | {r.get('category', '')} | {r.get('status', '')} "
              f"| {entity} | {title} |")


def cmd_show(args):
    """Show full details of a research object."""
    data = load_or_create(args.project)
    r = find_research(data, args.research_id)
    if not r:
        print(f"ERROR: Research '{args.research_id}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"## {r['id']}: {r['title']}")
    print(f"**Category**: {r['category']} | **Status**: {r['status']}")
    print(f"**Topic**: {r['topic']}")
    print()

    # Linked entity
    if r.get("linked_entity_type"):
        print(f"**Linked to**: {r['linked_entity_type']} {r.get('linked_entity_id', '')}")
    if r.get("linked_idea_id"):
        print(f"**Also linked to idea**: {r['linked_idea_id']}")
    if r.get("skill"):
        print(f"**Skill**: {r['skill']}")
    if r.get("file_path"):
        print(f"**File**: {r['file_path']}")
    if r.get("scopes"):
        print(f"**Scopes**: {', '.join(r['scopes'])}")
    if r.get("tags"):
        print(f"**Tags**: {', '.join(r['tags'])}")
    print()

    # Summary
    print("### Summary")
    print()
    print(r.get("summary", ""))
    print()

    # Key findings
    findings = r.get("key_findings", [])
    if findings:
        print(f"### Key Findings ({len(findings)})")
        print()
        for f in findings:
            print(f"- {f}")
        print()

    # Decision IDs
    decision_ids = r.get("decision_ids", [])
    if decision_ids:
        print(f"### Related Decisions: {', '.join(decision_ids)}")
        # Try to load decision details
        _s = JSONFileStorage()
        if _s.exists(args.project, 'decisions'):
            dec_data = _s.load_data(args.project, 'decisions')
            for d in dec_data.get("decisions", []):
                if d["id"] in decision_ids:
                    print(f"- **{d['id']}** ({d.get('type', '')}, {d.get('status', '')}): "
                          f"{d.get('issue', '')[:60]}")
        print()

    print(f"Created: {r.get('created_at', '')} by {r.get('created_by', 'unknown')}")
    print(f"Updated: {r.get('updated_at', '')}")


def cmd_update(args):
    """Update research objects."""
    try:
        updates = load_json_data(args.data)
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
    timestamp = now_iso()

    updated = []
    for u in updates:
        r = find_research(data, u["id"])
        if not r:
            print(f"  WARNING: Research {u['id']} not found, skipping", file=sys.stderr)
            continue

        # Status transition validation
        if "status" in u:
            new_status = u["status"]
            current_status = r.get("status", "DRAFT")
            if new_status not in VALID_TRANSITIONS.get(current_status, set()):
                print(f"  WARNING: Invalid transition {current_status} -> {new_status} for {u['id']}. "
                      f"Valid: {VALID_TRANSITIONS.get(current_status, set())}",
                      file=sys.stderr)
                continue

        # Update fields
        updatable = ["title", "topic", "status", "category", "summary",
                     "key_findings", "decision_ids", "file_path",
                     "linked_idea_id", "scopes", "tags"]
        for field in updatable:
            if field in u:
                r[field] = u[field]

        r["updated_at"] = timestamp
        updated.append(u["id"])

    save_json(args.project, data)

    if updated:
        print(f"Updated: {', '.join(updated)}")
    else:
        print("No research objects were updated.")


def cmd_context(args):
    """Load research context for an entity (objective or idea).

    Resolves research by:
    1. Direct match: linked_entity_id == entity_id
    2. Secondary match: linked_idea_id == entity_id
    3. Indirect (for objectives): ideas that advance this objective's KRs -> research linked to those ideas
    """
    data = load_or_create(args.project)
    entity_id = args.entity
    active = [r for r in data.get("research", []) if r.get("status") == "ACTIVE"]

    # Direct + secondary match
    matched = [r for r in active
               if r.get("linked_entity_id") == entity_id
               or r.get("linked_idea_id") == entity_id]
    matched_ids = {r["id"] for r in matched}

    # Indirect match: if entity is an objective, find ideas advancing it
    if entity_id.startswith("O-"):
        _s = JSONFileStorage()
        if _s.exists(args.project, 'ideas'):
            ideas_data = _s.load_data(args.project, 'ideas')
            idea_ids = set()
            for idea in ideas_data.get("ideas", []):
                for kr in idea.get("advances_key_results", []):
                    if kr.startswith(entity_id + "/"):
                        idea_ids.add(idea["id"])
                        break
            # Find research linked to those ideas
            for r in active:
                if r["id"] not in matched_ids:
                    if (r.get("linked_entity_id") in idea_ids
                            or r.get("linked_idea_id") in idea_ids):
                        matched.append(r)
                        matched_ids.add(r["id"])

    if not matched:
        print(f"No active research linked to {entity_id}.")
        return

    print(f"### Research for {entity_id} ({len(matched)})")
    print()
    for r in sorted(matched, key=lambda x: x["id"]):
        print(f"**{r['id']}**: {r['title']} [{r['category']}]")
        if r.get("summary"):
            print(f"  {r['summary']}")
        for f in (r.get("key_findings") or []):
            print(f"  - {f}")
        if r.get("decision_ids"):
            print(f"  Decisions: {', '.join(r['decision_ids'])}")
        if r.get("file_path"):
            print(f"  File: {r['file_path']}")
        print()


def cmd_contract(args):
    """Print contract spec."""
    if args.name not in CONTRACTS:
        print(f"ERROR: Unknown contract '{args.name}'. Available: {', '.join(sorted(CONTRACTS.keys()))}",
              file=sys.stderr)
        sys.exit(1)
    print(render_contract(args.name, CONTRACTS[args.name]))


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Research — structured analysis output")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Create research objects")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="List/filter research")
    p.add_argument("project")
    p.add_argument("--status", choices=sorted(VALID_STATUSES))
    p.add_argument("--category", choices=sorted(VALID_CATEGORIES))
    p.add_argument("--entity", help="Filter by linked entity ID (O-NNN or I-NNN)")

    p = sub.add_parser("show", help="Show research details")
    p.add_argument("project")
    p.add_argument("research_id")

    p = sub.add_parser("update", help="Update research")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("context", help="Research context for entity")
    p.add_argument("project")
    p.add_argument("--entity", required=True, help="Entity ID (O-NNN or I-NNN)")

    p = sub.add_parser("contract", help="Print contract spec (no project needed)")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))
    p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "read": cmd_read,
        "show": cmd_show,
        "update": cmd_update,
        "context": cmd_context,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
