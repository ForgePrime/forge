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

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from entity_base import EntityModule, make_cli
from storage import JSONFileStorage


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


# -- Module --

class Research(EntityModule):
    entity_type = "research"
    list_key = "research"
    id_prefix = "R"
    contracts = CONTRACTS
    display_name = "Research"
    dedup_keys = ("category", "title")

    def build_entity(self, input_item, entity_id, timestamp, args):
        category = input_item["category"].lower().strip()

        # Validate linked entity
        entity_type = input_item.get("linked_entity_type")
        entity_id_val = input_item.get("linked_entity_id")
        if entity_type and not entity_id_val:
            print(f"WARNING: linked_entity_type set but linked_entity_id missing for '{input_item['title']}'",
                  file=sys.stderr)
        if entity_id_val and not entity_type:
            print(f"WARNING: linked_entity_id set but linked_entity_type missing for '{input_item['title']}'",
                  file=sys.stderr)

        # Handle content -> file writing
        content = input_item.get("content")
        file_path = input_item.get("file_path")
        if content and not file_path:
            # Auto-generate file_path from skill + title
            skill = input_item.get("skill", "research")
            slug = input_item["title"].lower()
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

        return {
            "id": entity_id,
            "title": input_item["title"],
            "topic": input_item["topic"],
            "status": "DRAFT",
            "category": category,
            "linked_entity_type": entity_type,
            "linked_entity_id": entity_id_val,
            "linked_idea_id": input_item.get("linked_idea_id"),
            "skill": input_item.get("skill"),
            "file_path": file_path,
            "summary": input_item["summary"],
            "key_findings": input_item.get("key_findings", []),
            "decision_ids": input_item.get("decision_ids", []),
            "scopes": input_item.get("scopes", []),
            "tags": input_item.get("tags", []),
            "created_at": timestamp,
            "updated_at": timestamp,
            "created_by": input_item.get("created_by", "claude"),
        }

    def apply_filters(self, items, args):
        if getattr(args, "status", None):
            items = [r for r in items if r.get("status") == args.status]
        if getattr(args, "category", None):
            items = [r for r in items if r.get("category") == args.category.lower().strip()]
        if getattr(args, "entity", None):
            entity_id = args.entity
            items = [r for r in items
                     if r.get("linked_entity_id") == entity_id
                     or r.get("linked_idea_id") == entity_id]
        return items

    def render_list(self, items, args):
        print(f"## Research: {args.project}")
        filters = []
        if getattr(args, "status", None):
            filters.append(f"status={args.status}")
        if getattr(args, "category", None):
            filters.append(f"category={args.category}")
        if getattr(args, "entity", None):
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
            entity = r.get("linked_entity_id") or "\u2014"
            print(f"| {r['id']} | {r.get('category', '')} | {r.get('status', '')} "
                  f"| {entity} | {title} |")

    def apply_update(self, item, update, timestamp):
        # Status transition validation
        if "status" in update:
            new_status = update["status"]
            current_status = item.get("status", "DRAFT")
            if new_status not in VALID_TRANSITIONS.get(current_status, set()):
                print(f"  WARNING: Invalid transition {current_status} -> {new_status} for {update['id']}. "
                      f"Valid: {VALID_TRANSITIONS.get(current_status, set())}",
                      file=sys.stderr)
                return False

        # Update fields
        updatable = ["title", "topic", "status", "category", "summary",
                     "key_findings", "decision_ids", "file_path",
                     "linked_idea_id", "scopes", "tags"]
        for field in updatable:
            if field in update:
                item[field] = update[field]

        item["updated_at"] = timestamp


_mod = Research()

# Public API used by other modules
load_or_create = _mod.load
save_json = _mod.save
find_research = _mod.find_by_id


# -- Custom commands --

def cmd_show(args):
    """Show full details of a research object."""
    data = _mod.load(args.project)
    r = _mod.find_by_id(data, args.research_id)
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


def cmd_context(args):
    """Load research context for an entity (objective or idea).

    Resolves research by:
    1. Direct match: linked_entity_id == entity_id
    2. Secondary match: linked_idea_id == entity_id
    3. Indirect (for objectives): ideas that advance this objective's KRs -> research linked to those ideas
    """
    data = _mod.load(args.project)
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


# -- CLI --

def _setup_extra_parsers(sub):
    # Add filter args to the read parser created by make_cli
    read_parser = sub.choices["read"]
    read_parser.add_argument("--status", choices=sorted(VALID_STATUSES))
    read_parser.add_argument("--category", choices=sorted(VALID_CATEGORIES))
    read_parser.add_argument("--entity", help="Filter by linked entity ID (O-NNN or I-NNN)")

    p = sub.add_parser("show", help="Show research details")
    p.add_argument("project")
    p.add_argument("research_id")

    p = sub.add_parser("context", help="Research context for entity")
    p.add_argument("project")
    p.add_argument("--entity", required=True, help="Entity ID (O-NNN or I-NNN)")


def main():
    make_cli(
        _mod,
        extra_commands={
            "show": cmd_show,
            "context": cmd_context,
        },
        setup_extra_parsers=_setup_extra_parsers,
        description="Forge Research — structured analysis output",
    )


if __name__ == "__main__":
    main()
