"""
Knowledge — versioned, reusable knowledge objects (K-NNN).

Condensed, versioned knowledge that enriches LLM execution context.
Supports CRUD, versioning (embedded array), entity linking, and
basic impact analysis.

Usage:
    python -m core.knowledge <command> <project> [options]

Commands:
    add          {project} --data '{json}'         Create knowledge objects
    read         {project} [--status X] [--category X] [--scope X]  List/filter
    show         {project} {knowledge_id}          Full details + version history
    update       {project} --data '{json}'         Update (new version if content changed)
    link         {project} --data '{json}'         Link knowledge to entity
    unlink       {project} {knowledge_id} {index}  Remove link by index
    impact       {project} {knowledge_id}          Find all linked entities
    contract     {name}                            Print contract spec
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from entity_base import EntityModule
from errors import EntityNotFound, ValidationError
from models import Knowledge as KnowledgeModel
from storage import JSONFileStorage, now_iso
from trace import trace_cmd


# -- Constants --

VALID_CATEGORIES = {
    "domain-rules", "api-reference", "architecture", "business-context",
    "technical-context", "code-patterns", "integration", "infrastructure",
    "requirement", "source-document",
}

VALID_STATUSES = {"DRAFT", "ACTIVE", "REVIEW_NEEDED", "DEPRECATED", "ARCHIVED"}

VALID_TRANSITIONS = {
    "DRAFT": {"ACTIVE", "ARCHIVED"},
    "ACTIVE": {"REVIEW_NEEDED", "DEPRECATED"},
    "REVIEW_NEEDED": {"ACTIVE", "DEPRECATED"},
    "DEPRECATED": {"ARCHIVED", "ACTIVE"},
    "ARCHIVED": set(),
}

VALID_LINK_RELATIONS = {"required", "context", "reference"}

VALID_LINK_ENTITY_TYPES = {"task", "idea", "objective", "knowledge", "guideline", "lesson"}

VALID_SOURCE_TYPES = {"documentation", "lesson", "research", "user", "codebase", "ai-extraction"}


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["title", "category", "content"],
        "optional": ["scopes", "tags", "source", "linked_entities",
                      "dependencies", "review_interval_days", "created_by"],
        "enums": {
            "category": VALID_CATEGORIES,
        },
        "types": {
            "scopes": list,
            "tags": list,
            "linked_entities": list,
            "dependencies": list,
            "review_interval_days": int,
        },
        "invariant_texts": [
            "title: concise title for the knowledge object",
            "category: one of domain-rules, api-reference, architecture, business-context, "
            "technical-context, code-patterns, integration, infrastructure",
            "content: the knowledge content — clear, concise, reusable",
            "scopes: areas this applies to (e.g., ['backend', 'database'])",
            "tags: searchable keywords",
            "source: {type, ref, derived_from_lessons} — provenance",
            "linked_entities: [{entity_type, entity_id, relation}] — links to other entities",
            "dependencies: [K-NNN IDs] — knowledge this depends on",
            "review_interval_days: days between periodic reviews (default: 30)",
            "created_by: 'user' or 'ai' (default: 'user')",
        ],
        "example": [
            {
                "title": "Redis Stack — available data structures",
                "category": "technical-context",
                "content": "Redis Stack 7.4 supports: JSON, Search, TimeSeries, Graph, Bloom...",
                "scopes": ["backend", "database"],
                "tags": ["redis", "data-structures"],
                "source": {
                    "type": "documentation",
                    "ref": "https://redis.io/docs/stack/",
                    "derived_from_lessons": ["L-012"],
                },
            },
        ],
    },
    "update": {
        "required": ["id"],
        "optional": ["title", "content", "status", "category", "scopes", "tags",
                      "source", "dependencies", "review_interval_days",
                      "change_reason", "changed_by"],
        "enums": {
            "status": VALID_STATUSES,
            "category": VALID_CATEGORIES,
        },
        "types": {
            "scopes": list,
            "tags": list,
            "dependencies": list,
            "review_interval_days": int,
        },
        "invariant_texts": [
            "id: existing knowledge ID (K-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "If 'content' is changed, a new version is created automatically — "
            "requires 'change_reason' field",
            "status transitions: DRAFT→ACTIVE, ACTIVE→REVIEW_NEEDED, "
            "ACTIVE→DEPRECATED, REVIEW_NEEDED→ACTIVE, REVIEW_NEEDED→DEPRECATED, "
            "DEPRECATED→ARCHIVED, DEPRECATED→ACTIVE, DRAFT→ARCHIVED",
            "changed_by: 'user' or 'ai' (default: 'user')",
        ],
        "example": [
            {"id": "K-001", "status": "ACTIVE"},
            {"id": "K-003", "content": "Updated content...",
             "change_reason": "Added TimeSeries module info", "changed_by": "user"},
        ],
    },
    "link": {
        "required": ["knowledge_id", "entity_type", "entity_id", "relation"],
        "optional": [],
        "enums": {
            "entity_type": VALID_LINK_ENTITY_TYPES,
            "relation": VALID_LINK_RELATIONS,
        },
        "types": {},
        "invariant_texts": [
            "knowledge_id: K-NNN ID to add link to",
            "entity_type: one of task, idea, objective, knowledge, guideline, lesson",
            "entity_id: target entity ID (e.g., T-001, I-003, O-001, K-005)",
            "relation: 'required' (always in context), 'context' (if space), 'reference' (lookup only)",
        ],
        "example": [
            {"knowledge_id": "K-001", "entity_type": "task",
             "entity_id": "T-005", "relation": "required"},
        ],
    },
}


# -- Module --

class Knowledge(EntityModule):
    entity_type = "knowledge"
    list_key = "knowledge"
    id_prefix = "K"
    display_name = "Knowledge"
    dedup_keys = ("category", "title")
    contracts = CONTRACTS
    model_class = KnowledgeModel

    def build_entity(self, input_item, entity_id, timestamp, args):
        created_by = input_item.get("created_by", "user")

        # Build source object
        source = input_item.get("source", {})
        if not source.get("type"):
            source["type"] = "user"
        if source["type"] not in VALID_SOURCE_TYPES:
            print(f"WARNING: Unknown source type '{source['type']}'. "
                  f"Valid: {', '.join(sorted(VALID_SOURCE_TYPES))}",
                  file=sys.stderr)

        knowledge = {
            "id": entity_id,
            "title": input_item["title"],
            "category": input_item["category"].lower().strip(),
            "content": input_item["content"],
            "status": "DRAFT",
            "version": 1,
            "scopes": input_item.get("scopes", []),
            "tags": input_item.get("tags", []),
            "source": source,
            "linked_entities": input_item.get("linked_entities", []),
            "dependencies": input_item.get("dependencies", []),
            "versions": [
                {
                    "version": 1,
                    "content": input_item["content"],
                    "changed_by": created_by,
                    "changed_at": timestamp,
                    "change_reason": "Initial creation",
                },
            ],
            "review": {
                "last_reviewed_at": timestamp,
                "review_interval_days": input_item.get("review_interval_days", 30),
                "next_review_at": None,
            },
            "created_at": timestamp,
            "updated_at": timestamp,
            "created_by": created_by,
        }

        # Fidelity Chain: warn on compound requirements
        if knowledge["category"] == "requirement":
            self._warn_compound_requirement(knowledge["content"], entity_id)

        # Validate linked_entities if provided
        for le in knowledge["linked_entities"]:
            if le.get("entity_type") not in VALID_LINK_ENTITY_TYPES:
                print(f"WARNING: Invalid entity_type '{le.get('entity_type')}' in linked_entities",
                      file=sys.stderr)
            if le.get("relation") not in VALID_LINK_RELATIONS:
                print(f"WARNING: Invalid relation '{le.get('relation')}' in linked_entities",
                      file=sys.stderr)

        return knowledge

    @staticmethod
    def _warn_compound_requirement(content: str, entity_id: str):
        """Warn if a requirement appears compound (multiple independent clauses)."""
        compound_markers = [" and ", " oraz ", " + ", "; ", " & "]
        content_lower = content.lower()
        triggers = [m.strip() for m in compound_markers if m in content_lower]
        if triggers and len(content) > 100:
            print(f"  FIDELITY_WARNING: {entity_id} may be compound "
                  f"(markers: {triggers}, {len(content)} chars). "
                  f"Consider splitting into atomic requirements.",
                  file=sys.stderr)
        elif len(content) > 200:
            print(f"  FIDELITY_WARNING: {entity_id} content is {len(content)} chars. "
                  f"Long requirements risk losing fidelity during decomposition. "
                  f"Consider splitting.",
                  file=sys.stderr)

    def apply_filters(self, items, args):
        if args.status:
            items = [k for k in items if k.get("status") == args.status]
        if args.category:
            items = [k for k in items if k.get("category") == args.category.lower().strip()]
        if args.scope:
            scope = args.scope.lower().strip()
            items = [k for k in items if scope in k.get("scopes", [])]
        return items

    def render_list(self, items, args):
        print(f"## Knowledge: {args.project}")
        filters = []
        if args.status:
            filters.append(f"status={args.status}")
        if args.category:
            filters.append(f"category={args.category}")
        if args.scope:
            filters.append(f"scope={args.scope}")
        if filters:
            print(f"Filter: {', '.join(filters)}")
        print(f"Count: {len(items)}")
        print()

        if not items:
            print("(none)")
            return

        print("| ID | Category | Status | Version | Title |")
        print("|----|----------|--------|---------|-------|")
        for k in items:
            title = k.get("title", "")[:45]
            print(f"| {k['id']} | {k.get('category', '')} | {k.get('status', '')} "
                  f"| v{k.get('version', 1)} | {title} |")

    def apply_update(self, item, update, timestamp):
        # Status transition validation
        if "status" in update:
            new_status = update["status"]
            current_status = item.get("status", "DRAFT")
            if new_status not in VALID_TRANSITIONS.get(current_status, set()):
                print(f"  WARNING: Invalid transition {current_status} → {new_status} for {update['id']}. "
                      f"Valid: {VALID_TRANSITIONS.get(current_status, set())}",
                      file=sys.stderr)
                return False

        # Content change → new version
        if "content" in update and update["content"] != item.get("content"):
            if not update.get("change_reason"):
                print(f"  WARNING: Content change for {update['id']} requires 'change_reason'",
                      file=sys.stderr)
                return False
            new_version = item.get("version", 1) + 1
            item["versions"].append({
                "version": new_version,
                "content": update["content"],
                "changed_by": update.get("changed_by", "user"),
                "changed_at": timestamp,
                "change_reason": update["change_reason"],
            })
            item["version"] = new_version
            item["content"] = update["content"]

        # Update other fields
        updatable = ["title", "status", "category", "scopes", "tags",
                     "source", "dependencies"]
        for field in updatable:
            if field in update:
                item[field] = update[field]

        # Update review interval
        if "review_interval_days" in update:
            if "review" not in item:
                item["review"] = {}
            item["review"]["review_interval_days"] = update["review_interval_days"]

        item["updated_at"] = timestamp


_mod = Knowledge()

# Public API used by other modules
load_or_create = _mod.load
save_json = _mod.save
find_knowledge = _mod.find_by_id


# -- Custom commands --

def cmd_show(args):
    """Show full details of a knowledge object."""
    data = _mod.load(args.project)
    k = _mod.find_by_id(data, args.knowledge_id)
    if not k:
        raise EntityNotFound(f"Knowledge '{args.knowledge_id}' not found.")

    print(f"## {k['id']}: {k['title']}")
    print(f"**Category**: {k['category']} | **Status**: {k['status']} | **Version**: v{k.get('version', 1)}")
    if k.get("scopes"):
        print(f"**Scopes**: {', '.join(k['scopes'])}")
    if k.get("tags"):
        print(f"**Tags**: {', '.join(k['tags'])}")
    print()

    # Content
    print("### Content")
    print()
    print(k.get("content", ""))
    print()

    # Source
    source = k.get("source", {})
    if source:
        print("### Source")
        print(f"- **Type**: {source.get('type', 'unknown')}")
        if source.get("ref"):
            print(f"- **Reference**: {source['ref']}")
        if source.get("derived_from_lessons"):
            print(f"- **Derived from lessons**: {', '.join(source['derived_from_lessons'])}")
        print()

    # Linked entities
    links = k.get("linked_entities", [])
    if links:
        print("### Linked Entities")
        print()
        print("| # | Entity Type | Entity ID | Relation |")
        print("|---|-------------|-----------|----------|")
        for i, le in enumerate(links):
            print(f"| {i} | {le['entity_type']} | {le['entity_id']} | {le['relation']} |")
        print()

    # Dependencies
    deps = k.get("dependencies", [])
    if deps:
        print(f"### Dependencies: {', '.join(deps)}")
        print()

    # Review
    review = k.get("review", {})
    if review:
        print("### Review")
        print(f"- **Last reviewed**: {review.get('last_reviewed_at', 'never')}")
        print(f"- **Interval**: {review.get('review_interval_days', 30)} days")
        if review.get("next_review_at"):
            print(f"- **Next review**: {review['next_review_at']}")
        print()

    # Version history
    versions = k.get("versions", [])
    if versions:
        print("### Version History")
        print()
        print("| Version | Changed By | Changed At | Reason |")
        print("|---------|------------|------------|--------|")
        for v in sorted(versions, key=lambda x: x.get("version", 0), reverse=True):
            reason = v.get("change_reason", "")[:50]
            print(f"| v{v['version']} | {v.get('changed_by', '')} | {v.get('changed_at', '')} | {reason} |")

    print()
    print(f"Created: {k.get('created_at', '')} by {k.get('created_by', 'unknown')}")
    print(f"Updated: {k.get('updated_at', '')}")


def cmd_link(args):
    """Link knowledge to an entity."""
    from contracts import validate_contract
    from storage import load_json_data
    import json

    try:
        link_data = load_json_data(args.data)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")

    if not isinstance(link_data, list):
        link_data = [link_data]

    errors = validate_contract(CONTRACTS["link"], link_data)
    if errors:
        details = "; ".join(errors[:10])
        raise ValidationError(f"{len(errors)} validation issues: {details}")

    data = _mod.load(args.project)

    for ld in link_data:
        k = _mod.find_by_id(data, ld["knowledge_id"])
        if not k:
            print(f"  WARNING: Knowledge {ld['knowledge_id']} not found", file=sys.stderr)
            continue

        # Dedup: check if link already exists
        existing = k.get("linked_entities", [])
        for le in existing:
            if le["entity_type"] == ld["entity_type"] and le["entity_id"] == ld["entity_id"]:
                print(f"  Link already exists: {ld['knowledge_id']} → "
                      f"{ld['entity_type']}:{ld['entity_id']} (updating relation)")
                le["relation"] = ld["relation"]
                break
        else:
            existing.append({
                "entity_type": ld["entity_type"],
                "entity_id": ld["entity_id"],
                "relation": ld["relation"],
            })
            k["linked_entities"] = existing
            print(f"  Linked: {ld['knowledge_id']} → {ld['entity_type']}:{ld['entity_id']} "
                  f"(relation={ld['relation']})")

        k["updated_at"] = now_iso()

    _mod.save(args.project, data)
    for ld in link_data:
        trace_cmd(args.project, "knowledge", "link",
                  knowledge_id=ld["knowledge_id"],
                  entity=f"{ld['entity_type']}:{ld['entity_id']}")


def cmd_unlink(args):
    """Remove link by index."""
    data = _mod.load(args.project)
    k = _mod.find_by_id(data, args.knowledge_id)
    if not k:
        raise EntityNotFound(f"Knowledge '{args.knowledge_id}' not found.")

    links = k.get("linked_entities", [])
    if not links:
        raise EntityNotFound(f"No links on '{args.knowledge_id}' to remove.")
    index = int(args.index)
    if index < 0 or index >= len(links):
        raise ValidationError(f"Link index {index} out of range (0-{len(links) - 1}).")

    removed = links.pop(index)
    k["updated_at"] = now_iso()
    _mod.save(args.project, data)
    trace_cmd(args.project, "knowledge", "unlink",
              knowledge_id=args.knowledge_id,
              removed=f"{removed['entity_type']}:{removed['entity_id']}")
    print(f"Removed link: {args.knowledge_id} → {removed['entity_type']}:{removed['entity_id']}")


def cmd_impact(args):
    """Find all entities that reference this knowledge object."""
    storage = JSONFileStorage()
    data = _mod.load(args.project)
    k = _mod.find_by_id(data, args.knowledge_id)
    if not k:
        raise EntityNotFound(f"Knowledge '{args.knowledge_id}' not found.")

    k_id = args.knowledge_id
    print(f"## Impact Analysis: {k_id} — {k['title']}")
    print()

    impacts = []

    # 1. Direct linked entities from this knowledge object
    for le in k.get("linked_entities", []):
        impacts.append({
            "source": "linked_entity",
            "entity_type": le["entity_type"],
            "entity_id": le["entity_id"],
            "relation": le["relation"],
        })

    # 2. Scan tracker.json for tasks with knowledge_ids referencing this K-NNN
    if storage.exists(args.project, 'tracker'):
        tracker = storage.load_data(args.project, 'tracker')
        for task in tracker.get("tasks", []):
            if k_id in task.get("knowledge_ids", []):
                impacts.append({
                    "source": "task.knowledge_ids",
                    "entity_type": "task",
                    "entity_id": task["id"],
                    "relation": "uses",
                    "detail": f"{task['name']} [{task['status']}]",
                })

    # 3. Scan ideas.json for ideas with knowledge_ids
    if storage.exists(args.project, 'ideas'):
        ideas = storage.load_data(args.project, 'ideas')
        for idea in ideas.get("ideas", []):
            if k_id in idea.get("knowledge_ids", []):
                impacts.append({
                    "source": "idea.knowledge_ids",
                    "entity_type": "idea",
                    "entity_id": idea["id"],
                    "relation": "uses",
                    "detail": f"{idea['title']} [{idea['status']}]",
                })

    # 4. Scan objectives.json for objectives with knowledge_ids
    if storage.exists(args.project, 'objectives'):
        objectives = storage.load_data(args.project, 'objectives')
        for obj in objectives.get("objectives", []):
            if k_id in obj.get("knowledge_ids", []):
                impacts.append({
                    "source": "objective.knowledge_ids",
                    "entity_type": "objective",
                    "entity_id": obj["id"],
                    "relation": "uses",
                    "detail": f"{obj['title']} [{obj['status']}]",
                })

    # 5. Scan other knowledge objects for dependencies
    for other_k in data.get("knowledge", []):
        if other_k["id"] != k_id and k_id in other_k.get("dependencies", []):
            impacts.append({
                "source": "knowledge.dependencies",
                "entity_type": "knowledge",
                "entity_id": other_k["id"],
                "relation": "depends_on",
                "detail": f"{other_k['title']} [{other_k['status']}]",
            })

    if not impacts:
        print("No entities reference this knowledge object.")
        return

    print(f"Found {len(impacts)} references:")
    print()
    print("| Source | Entity Type | Entity ID | Relation | Detail |")
    print("|--------|-------------|-----------|----------|--------|")
    for imp in impacts:
        detail = imp.get("detail", "")
        print(f"| {imp['source']} | {imp['entity_type']} | {imp['entity_id']} "
              f"| {imp['relation']} | {detail} |")

    # Warn about active tasks
    active_tasks = [i for i in impacts
                    if i["entity_type"] == "task"
                    and i.get("detail", "").endswith(("TODO]", "IN_PROGRESS]"))]
    if active_tasks:
        print()
        print(f"WARNING: {len(active_tasks)} active task(s) reference this knowledge — "
              f"changes may affect them.", file=sys.stderr)


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Knowledge — versioned knowledge objects")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Create knowledge objects")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="List/filter knowledge")
    p.add_argument("project")
    p.add_argument("--status", choices=sorted(VALID_STATUSES))
    p.add_argument("--category", choices=sorted(VALID_CATEGORIES))
    p.add_argument("--scope")

    p = sub.add_parser("show", help="Show knowledge details")
    p.add_argument("project")
    p.add_argument("knowledge_id")

    p = sub.add_parser("update", help="Update knowledge")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("link", help="Link knowledge to entity")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("unlink", help="Remove link")
    p.add_argument("project")
    p.add_argument("knowledge_id")
    p.add_argument("index")

    p = sub.add_parser("impact", help="Impact analysis")
    p.add_argument("project")
    p.add_argument("knowledge_id")

    p = sub.add_parser("contract", help="Print contract spec (no project needed)")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))
    p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    commands = {
        "add": _mod.cmd_add,
        "read": _mod.cmd_read,
        "show": cmd_show,
        "update": _mod.cmd_update,
        "link": cmd_link,
        "unlink": cmd_unlink,
        "impact": cmd_impact,
        "contract": _mod.cmd_contract,
    }

    from errors import ForgeError
    try:
        commands[args.command](args)
    except ForgeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
