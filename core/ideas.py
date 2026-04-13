"""
Ideas — staging area for proposals, plans, and directions before execution.

Ideas are the layer BETWEEN "I have a thought" and "let's build it".
They provide a space to explore, assess risks, design architecture,
and mature a proposal before committing it to the task pipeline.

Ideas support hierarchy (parent_id) and typed relations (depends_on,
related_to, supersedes, duplicates) for organizing complex proposals
into sub-ideas and tracking dependencies.

Lifecycle:
    DRAFT → EXPLORING → APPROVED → COMMITTED
          ↘ REJECTED (with reason)    ↗

- DRAFT: initial capture, not yet analyzed
- EXPLORING: deep-* analysis in progress (discover, risk, feasibility, etc.)
- APPROVED: approved for implementation, not yet in pipeline
- COMMITTED: materialized into task graph via /plan (terminal state)
- REJECTED: discarded (with reason, or merged_into another idea)

Decisions created during exploration reference the idea via task_id: "I-NNN".
When committed, tasks in the pipeline carry origin: "I-NNN" for traceability.
Explorations and risks are stored as decisions (type=exploration, type=risk)
in decisions.json, linked via task_id or linked_entity_id.

Usage:
    python -m core.ideas <command> <project> [options]

Commands:
    add      {project} --data '{json}'              Add ideas
    read     {project} [--status X] [--category X] [--parent X]  Read ideas
    update   {project} --data '{json}'              Update idea fields/status
    show     {project} {idea_id}                    Show full idea details
    commit   {project} {idea_id}                    Mark APPROVED idea as COMMITTED
    contract {name}                                 Print contract spec
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from entity_base import EntityModule, make_cli
from errors import ValidationError, EntityNotFound, PreconditionError
from models import Idea
from storage import JSONFileStorage, load_json_data, now_iso
from trace import trace_cmd


# -- Constants --

VALID_CATEGORIES = {"feature", "improvement", "experiment",
                    "migration", "refactor", "infrastructure",
                    "business-opportunity", "research"}

VALID_STATUSES = {"DRAFT", "EXPLORING", "APPROVED",
                  "COMMITTED", "REJECTED"}

# Valid status transitions (via cmd_update only).
# APPROVED → COMMITTED is handled by cmd_commit (or pipeline approve-plan), not update.
VALID_TRANSITIONS = {
    "DRAFT": {"EXPLORING", "REJECTED"},
    "EXPLORING": {"APPROVED", "REJECTED", "DRAFT"},
    "APPROVED": {"REJECTED"},
    "REJECTED": {"DRAFT"},  # can reopen
    "COMMITTED": set(),  # terminal — no transitions allowed
}

# Valid relation types between ideas
VALID_RELATION_TYPES = {"depends_on", "related_to", "supersedes", "duplicates"}


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["title", "description"],
        "optional": ["category", "priority", "tags", "related_ideas",
                      "guidelines", "parent_id", "relations", "scopes",
                      "advances_key_results", "knowledge_ids"],
        "enums": {
            "category": {"feature", "improvement", "experiment",
                         "migration", "refactor", "infrastructure",
                         "business-opportunity", "research"},
            "priority": {"HIGH", "MEDIUM", "LOW"},
        },
        "types": {
            "tags": list,
            "related_ideas": list,
            "guidelines": list,
            "relations": list,
            "scopes": list,
            "advances_key_results": list,
            "knowledge_ids": list,
        },
        "invariant_texts": [
            "title: concise name for the idea (e.g., 'Add Redis caching to API')",
            "description: what you want to achieve and why — enough for exploration to begin",
            "category: what kind of work this is (feature, improvement, experiment, migration, refactor, infrastructure, business-opportunity, research)",
            "priority: HIGH (urgent/blocking), MEDIUM (planned), LOW (nice-to-have)",
            "tags: searchable keywords",
            "related_ideas: (legacy) list of idea IDs — prefer 'relations' for new ideas",
            "guidelines: list of guideline IDs that apply to this idea (e.g., ['G-001'])",
            "parent_id: parent idea ID for hierarchy (e.g., 'I-001'). Null/omitted for root ideas.",
            "relations: typed edges to other ideas. Each: {type: 'depends_on|related_to|supersedes|duplicates', target_id: 'I-NNN'}",
            "scopes: list of guideline scopes this idea relates to (e.g., ['backend', 'database']). Used to load applicable guidelines during /discover and /plan.",
            "advances_key_results: list of Key Result IDs this idea advances (format: 'O-001/KR-1'). Links idea to business objectives.",
            "knowledge_ids: list of Knowledge IDs (K-001, etc.) that provide context for this idea. Loaded during /discover and /plan.",
        ],
        "example": [
            {
                "title": "Trading Platform",
                "description": "Build an automated trading platform with signal generation, backtesting, and portfolio management.",
                "category": "feature",
                "priority": "HIGH",
                "tags": ["trading", "platform"],
                "scopes": ["trading", "backend"],
            },
            {
                "title": "Signal Generation Module",
                "description": "Generate buy/sell signals based on technical indicators and ML models.",
                "category": "feature",
                "priority": "HIGH",
                "parent_id": "I-001",
                "relations": [
                    {"type": "depends_on", "target_id": "I-003"},
                ],
            },
        ],
    },
    "update": {
        "required": ["id"],
        "optional": ["title", "description", "status", "category",
                      "priority", "rejection_reason", "merged_into",
                      "tags", "related_ideas", "guidelines",
                      "exploration_notes", "parent_id", "relations",
                      "scopes", "advances_key_results", "knowledge_ids"],
        "enums": {
            "status": {"DRAFT", "EXPLORING", "APPROVED",
                        "REJECTED"},
            "category": {"feature", "improvement", "experiment",
                         "migration", "refactor", "infrastructure",
                         "business-opportunity", "research"},
            "priority": {"HIGH", "MEDIUM", "LOW"},
        },
        "types": {
            "tags": list,
            "related_ideas": list,
            "guidelines": list,
            "relations": list,
            "scopes": list,
            "advances_key_results": list,
            "knowledge_ids": list,
        },
        "invariant_texts": [
            "id: existing idea ID (I-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "status transitions: DRAFT→EXPLORING/REJECTED, EXPLORING→APPROVED/REJECTED/DRAFT, "
            "APPROVED→REJECTED, REJECTED→DRAFT",
            "REJECTED: set rejection_reason explaining why",
            "REJECTED+merged_into: idea absorbed by another (e.g., merged_into='I-005')",
            "COMMITTED status is set only by the `commit` command, not by update",
            "exploration_notes: free-text notes from analysis (appended, not replaced)",
            "relations: new relations are ADDED to existing ones (not replaced)",
        ],
        "example": [
            {"id": "I-001", "status": "EXPLORING"},
            {"id": "I-002", "status": "REJECTED",
             "rejection_reason": "Too risky for current phase, revisit in Q3"},
            {"id": "I-004", "status": "APPROVED"},
            {"id": "I-006", "relations": [
                {"type": "depends_on", "target_id": "I-001"}
            ]},
        ],
    },
}


# -- Module --

class Ideas(EntityModule):
    entity_type = "ideas"
    list_key = "ideas"
    id_prefix = "I"
    display_name = "Ideas"
    contracts = CONTRACTS
    dedup_keys = ()  # ideas don't dedup
    model_class = Idea

    def load(self, project: str) -> dict:
        """Load with migration: READY → APPROVED, PARKED → DRAFT."""
        data = self.storage.load_data(project, self.entity_type)
        # Migration: READY → APPROVED, PARKED → DRAFT
        for idea in data.get("ideas", []):
            if idea.get("status") == "READY":
                idea["status"] = "APPROVED"
            elif idea.get("status") == "PARKED":
                idea["status"] = "DRAFT"
                existing = idea.get("exploration_notes", "")
                separator = "\n\n---\n\n" if existing else ""
                idea["exploration_notes"] = existing + separator + "--- Unparked (auto-migrated from PARKED status)"
        return data

    def build_entity(self, input_item, entity_id, timestamp, args):
        """Create idea dict from input."""
        data = self.load(args.project)
        existing_idea_ids = {i["id"] for i in data.get("ideas", [])}

        # Validate parent_id
        parent_id = input_item.get("parent_id")
        if parent_id and parent_id not in existing_idea_ids:
            print(f"  WARNING: parent_id '{parent_id}' not found in ideas",
                  file=sys.stderr)

        # Validate relations
        relations = input_item.get("relations", [])
        validated_relations = []
        for rel in relations:
            if not isinstance(rel, dict):
                print(f"  WARNING: relation must be an object, skipping: {rel}",
                      file=sys.stderr)
                continue
            rel_type = rel.get("type", "")
            if rel_type not in VALID_RELATION_TYPES:
                print(f"  WARNING: invalid relation type '{rel_type}', "
                      f"valid: {', '.join(sorted(VALID_RELATION_TYPES))}",
                      file=sys.stderr)
                continue
            validated_relations.append({
                "type": rel_type,
                "target_id": rel.get("target_id", ""),
            })

        return {
            "id": entity_id,
            "title": input_item["title"],
            "description": input_item["description"],
            "category": input_item.get("category", "feature"),
            "priority": input_item.get("priority", "MEDIUM"),
            "tags": input_item.get("tags", []),
            "related_ideas": input_item.get("related_ideas", []),
            "guidelines": input_item.get("guidelines", []),
            "parent_id": parent_id,
            "relations": validated_relations,
            "scopes": input_item.get("scopes", []),
            "advances_key_results": input_item.get("advances_key_results", []),
            "knowledge_ids": input_item.get("knowledge_ids", []),
            "status": "DRAFT",
            "rejection_reason": "",
            "merged_into": "",
            "exploration_notes": "",
            "committed_at": None,
            "created": timestamp,
            "updated": timestamp,
        }

    def print_add_summary(self, project, data, added, skipped):
        status_counts = _status_counts(data)
        print(f"Ideas saved: {project}")
        print(f"  Added: {len(added)} ({', '.join(added)})")
        print(f"  Total: {len(data['ideas'])} | {_format_counts(status_counts)}")

    def apply_filters(self, items, args):
        """Filter by status, category, parent."""
        if args.status:
            items = [i for i in items if i.get("status") == args.status]
        if args.category:
            items = [i for i in items if i.get("category") == args.category]
        if hasattr(args, "parent") and args.parent:
            if args.parent == "root":
                items = [i for i in items if not i.get("parent_id")]
            else:
                items = [i for i in items if i.get("parent_id") == args.parent]
        return items

    def render_list(self, items, args):
        """Table with hierarchy column."""
        print(f"## Ideas: {args.project}")
        filters = []
        if args.status:
            filters.append(f"status={args.status}")
        if args.category:
            filters.append(f"category={args.category}")
        if hasattr(args, "parent") and args.parent:
            filters.append(f"parent={args.parent}")
        if filters:
            print(f"Filter: {', '.join(filters)}")
        print(f"Count: {len(items)}")
        print()

        if not items:
            print("(none)")
            return

        print("| ID | Parent | Category | Priority | Title | Status |")
        print("|----|--------|----------|----------|-------|--------|")
        for i in items:
            title = i.get("title", "")[:40]
            status = i.get("status", "")
            parent = i.get("parent_id", "") or "\u2014"
            if status == "REJECTED" and i.get("merged_into"):
                status = f"MERGED\u2192{i['merged_into']}"
            print(f"| {i['id']} | {parent} | {i.get('category', '')} | {i.get('priority', '')} | {title} | {status} |")

    def cmd_update(self, args):
        """Update idea fields and status with complex validation."""
        try:
            updates = load_json_data(args.data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

        if not isinstance(updates, list):
            updates = [updates]

        from contracts import validate_contract
        errors = validate_contract(CONTRACTS["update"], updates)
        if errors:
            details = "; ".join(errors[:10])
            raise ValidationError(f"{len(errors)} validation issues: {details}")

        data = self.load(args.project)
        timestamp = now_iso()

        updated = []
        for u in updates:
            idea = None
            for i in data.get("ideas", []):
                if i["id"] == u["id"]:
                    idea = i
                    break
            if idea is None:
                print(f"  WARNING: Idea {u['id']} not found, skipping", file=sys.stderr)
                continue

            # Validate status transition
            if "status" in u:
                new_status = u["status"]
                current = idea["status"]
                if current == "COMMITTED":
                    print(f"  WARNING: Idea {u['id']} is COMMITTED (terminal state), cannot change status", file=sys.stderr)
                    continue
                if new_status not in VALID_TRANSITIONS.get(current, set()):
                    print(f"  WARNING: Invalid transition {current}\u2192{new_status} for {u['id']}. "
                          f"Valid: {', '.join(sorted(VALID_TRANSITIONS.get(current, set()))) or 'none'}",
                          file=sys.stderr)
                    continue

            # Apply updates
            updatable = ["title", "description", "status", "category", "priority",
                         "rejection_reason", "merged_into", "tags", "related_ideas",
                         "guidelines", "parent_id", "scopes", "advances_key_results",
                         "knowledge_ids"]
            for field in updatable:
                if field in u:
                    idea[field] = u[field]

            # exploration_notes: append, not replace
            if "exploration_notes" in u:
                existing = idea.get("exploration_notes", "")
                separator = "\n\n---\n\n" if existing else ""
                idea["exploration_notes"] = existing + separator + u["exploration_notes"]

            # relations: append-merge (add new, don't replace existing)
            if "relations" in u:
                existing_rels = idea.get("relations", [])
                existing_keys = {(r.get("type"), r.get("target_id")) for r in existing_rels}
                for rel in u["relations"]:
                    if not isinstance(rel, dict):
                        continue
                    rel_type = rel.get("type", "")
                    target = rel.get("target_id", "")
                    if rel_type not in VALID_RELATION_TYPES:
                        print(f"  WARNING: invalid relation type '{rel_type}', skipping",
                              file=sys.stderr)
                        continue
                    if (rel_type, target) not in existing_keys:
                        existing_rels.append({"type": rel_type, "target_id": target})
                        existing_keys.add((rel_type, target))
                idea["relations"] = existing_rels

            idea["updated"] = timestamp
            updated.append(u["id"])

        self.save(args.project, data)
        trace_cmd(args.project, "ideas", "update",
                  updated=updated,
                  status_changes={u["id"]: u.get("status")
                                  for u in updates
                                  if u["id"] in updated and "status" in u})

        status_counts = _status_counts(data)
        print(f"Updated {len(updated)} ideas: {args.project}")
        for idea_id in updated:
            idea = next(i for i in data["ideas"] if i["id"] == idea_id)
            print(f"  {idea_id}: {idea.get('title', '')[:40]} ({idea.get('status', '')})")
        print(f"  {_format_counts(status_counts)}")


_mod = Ideas()

# Public API used by other modules
load_or_create = _mod.load
save_json = _mod.save
find_idea = _mod.find_by_id

# Expose commands as module-level functions (used by tests and other modules)
cmd_add = _mod.cmd_add
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update


def ideas_path(project: str) -> str:
    """Return the path to the ideas JSON file for a project."""
    return str(_mod.storage._path(project, 'ideas'))


# -- Custom commands (standalone) --

def cmd_show(args):
    """Show full details for a single idea."""
    storage = JSONFileStorage()
    if not storage.exists(args.project, 'ideas'):
        raise EntityNotFound(f"No ideas for '{args.project}' yet.")

    data = storage.load_data(args.project, 'ideas')
    idea_obj = _mod.find_by_id(data, args.idea_id)
    if idea_obj is None:
        raise EntityNotFound(f"Idea '{args.idea_id}' not found.")
    idea = idea_obj
    dec_data = None  # loaded on demand below

    print(f"## Idea {idea['id']}: {idea['title']}")
    print()
    print(f"- **Status**: {idea['status']}")
    print(f"- **Category**: {idea.get('category', '')}")
    print(f"- **Priority**: {idea.get('priority', '')}")
    if idea.get("parent_id"):
        print(f"- **Parent**: {idea['parent_id']}")
    print(f"- **Created**: {idea.get('created', '')}")
    print(f"- **Updated**: {idea.get('updated', '')}")
    if idea.get("tags"):
        print(f"- **Tags**: {', '.join(idea['tags'])}")
    if idea.get("scopes"):
        print(f"- **Scopes**: {', '.join(idea['scopes'])}")
    if idea.get("related_ideas"):
        print(f"- **Related (legacy)**: {', '.join(idea['related_ideas'])}")
    if idea.get("guidelines"):
        print(f"- **Guidelines**: {', '.join(idea['guidelines'])}")
    if idea.get("advances_key_results"):
        print(f"- **Advances KRs**: {', '.join(idea['advances_key_results'])}")
    if idea.get("knowledge_ids"):
        print(f"- **Knowledge**: {', '.join(idea['knowledge_ids'])}")
    print()

    # Hierarchy — show parent chain and children
    all_ideas = data.get("ideas", [])
    if idea.get("parent_id"):
        chain = _get_parent_chain(all_ideas, idea["id"])
        if chain:
            print(f"### Hierarchy: {' \u2192 '.join(chain)}")
            print()

    children = [i for i in all_ideas if i.get("parent_id") == idea["id"]]
    if children:
        print(f"### Children ({len(children)})")
        for c in children:
            print(f"- **{c['id']}**: {c['title']} ({c['status']})")
        print()

    # Relations
    relations = idea.get("relations", [])
    if relations:
        print(f"### Relations ({len(relations)})")
        for rel in relations:
            print(f"- {rel.get('type', '')}: {rel.get('target_id', '')}")
        print()

    # Reverse relations (other ideas pointing to this one)
    reverse_rels = []
    for other in all_ideas:
        if other["id"] == idea["id"]:
            continue
        for rel in other.get("relations", []):
            if rel.get("target_id") == idea["id"]:
                reverse_rels.append({"from": other["id"], "type": rel["type"]})
    if reverse_rels:
        print(f"### Referenced By ({len(reverse_rels)})")
        for rr in reverse_rels:
            print(f"- {rr['from']} ({rr['type']})")
        print()

    print("### Description")
    print(idea.get("description", ""))
    print()

    if idea.get("exploration_notes"):
        print("### Exploration Notes (legacy)")
        print(idea["exploration_notes"])
        print()

    # Show explorations and risks from decisions.json (type=exploration, type=risk)
    if storage.exists(args.project, 'decisions'):
        dec_data = storage.load_data(args.project, 'decisions')
        all_decisions = dec_data.get("decisions", [])

        # Explorations: type=exploration with task_id or linked_entity_id matching idea
        related_exps = [d for d in all_decisions
                        if d.get("type") == "exploration"
                        and (d.get("task_id") == idea["id"]
                             or d.get("linked_entity_id") == idea["id"])]
        if related_exps:
            print(f"### Explorations ({len(related_exps)})")
            print()
            for e in related_exps:
                etype = e.get("exploration_type", "")
                summary = e.get("recommendation", "") or e.get("issue", "")
                print(f"- **{e['id']}** ({etype}): {summary[:60]}")
            print()

        # Risks: type=risk with linked_entity_id matching idea
        related_risks = [d for d in all_decisions
                         if d.get("type") == "risk"
                         and (d.get("linked_entity_id") == idea["id"]
                              or d.get("task_id") == idea["id"])]
        if related_risks:
            print(f"### Risks ({len(related_risks)})")
            print()
            for r in related_risks:
                print(f"- **{r['id']}** [{r.get('severity', '')}/{r.get('likelihood', '')}] "
                      f"({r.get('status', '')}): {r.get('issue', '')}")
            print()

    if idea.get("rejection_reason"):
        print("### Rejection Reason")
        print(idea["rejection_reason"])
        print()

    if idea.get("merged_into"):
        print(f"**Merged into**: {idea['merged_into']}")
        print()

    if idea.get("committed_at"):
        print(f"**Committed at**: {idea['committed_at']}")
        print()

    # Show other related decisions (not exploration/risk, those are shown above)
    if storage.exists(args.project, 'decisions'):
        if not dec_data:
            dec_data = storage.load_data(args.project, 'decisions')
        other_decisions = [d for d in dec_data.get("decisions", [])
                           if d.get("task_id") == idea["id"]
                           and d.get("type") not in ("exploration", "risk")]
        if other_decisions:
            print(f"### Related Decisions ({len(other_decisions)})")
            print()
            for d in other_decisions:
                print(f"- **{d['id']}** ({d.get('status', '')}): {d.get('issue', '')}")
                if d.get("recommendation"):
                    print(f"  \u2192 {d['recommendation']}")
            print()

    # Next steps hint
    if idea["status"] == "DRAFT":
        print("**Next**: `/discover {id}` to analyze this idea")
    elif idea["status"] == "EXPLORING":
        print("**Next**: Update to APPROVED when analysis is complete, or REJECTED if not viable")
    elif idea["status"] == "APPROVED":
        print(f"**Next**: `/plan {idea['id']}` to create task graph from this idea")


def cmd_commit(args):
    """Mark an APPROVED idea as COMMITTED — ready for /plan."""
    data = _mod.load(args.project)
    idea_obj = _mod.find_by_id(data, args.idea_id)
    if idea_obj is None:
        raise EntityNotFound(f"Idea '{args.idea_id}' not found.")
    idea = idea_obj

    if idea["status"] != "APPROVED":
        hint = ""
        if idea["status"] == "DRAFT":
            hint = " Explore it first: /discover {id} or update to EXPLORING"
        elif idea["status"] == "EXPLORING":
            hint = " Analysis still in progress. Update to APPROVED when done."
        raise PreconditionError(
            f"Idea {args.idea_id} must be APPROVED before commit (is {idea['status']}).{hint}")

    # Validate depends_on relations — all targets must be APPROVED or COMMITTED
    all_ideas = {i["id"]: i for i in data.get("ideas", [])}
    deps = [r for r in idea.get("relations", []) if r.get("type") == "depends_on"]
    unmet = []
    for dep in deps:
        target_id = dep.get("target_id", "")
        target = all_ideas.get(target_id)
        if not target:
            unmet.append(f"{target_id} (not found)")
        elif target["status"] not in ("APPROVED", "COMMITTED"):
            unmet.append(f"{target_id} (status: {target['status']})")
    if unmet:
        details = "; ".join(f"- {u}" for u in unmet)
        raise PreconditionError(
            f"Idea {args.idea_id} has unmet depends_on relations: {details}. "
            f"All dependencies must be APPROVED or COMMITTED first.")

    idea["status"] = "COMMITTED"
    idea["committed_at"] = now_iso()
    idea["updated"] = now_iso()

    _mod.save(args.project, data)
    trace_cmd(args.project, "ideas", "commit", idea_id=args.idea_id)

    # Present context for /plan
    print(f"## Idea {idea['id']} committed: {idea['title']}")
    print()
    print(f"**Category**: {idea.get('category', '')}")
    print(f"**Priority**: {idea.get('priority', '')}")
    print()
    print("### Description")
    print(idea.get("description", ""))
    print()

    if idea.get("exploration_notes"):
        print("### Exploration Summary")
        print(idea["exploration_notes"])
        print()

    if idea.get("guidelines"):
        print(f"### Linked Guidelines: {', '.join(idea['guidelines'])}")
        print()

    # Show related decisions
    storage = JSONFileStorage()
    if storage.exists(args.project, 'decisions'):
        dec_data = storage.load_data(args.project, 'decisions')
        related = [d for d in dec_data.get("decisions", [])
                   if d.get("task_id") == idea["id"]]
        open_decisions = [d for d in related if d.get("status") == "OPEN"]
        closed_decisions = [d for d in related if d.get("status") == "CLOSED"]

        if open_decisions:
            print(f"### Open Decisions ({len(open_decisions)}) \u2014 resolve before /plan")
            for d in open_decisions:
                print(f"- **{d['id']}**: {d.get('issue', '')}")
            print()

        if closed_decisions:
            print(f"### Resolved Decisions ({len(closed_decisions)})")
            for d in closed_decisions:
                rec = d.get("recommendation", "")
                override = d.get("override_value", "")
                value = override if override else rec
                print(f"- **{d['id']}**: {d.get('issue', '')} \u2192 {value}")
            print()

    print("### Next Step")
    print(f"Run `/plan {idea['id']}` to create task graph.")
    print(f"Tasks will carry `origin: \"{idea['id']}\"` for traceability.")


# -- Helpers --

def _status_counts(data: dict) -> dict:
    counts = {}
    for i in data.get("ideas", []):
        s = i.get("status", "DRAFT")
        counts[s] = counts.get(s, 0) + 1
    return counts


def _format_counts(counts: dict) -> str:
    parts = []
    for status in ["DRAFT", "EXPLORING", "APPROVED",
                    "COMMITTED", "REJECTED"]:
        if counts.get(status, 0) > 0:
            parts.append(f"{status}: {counts[status]}")
    return " | ".join(parts) if parts else "empty"


def _get_parent_chain(all_ideas: list, idea_id: str) -> list:
    """Build parent chain from root to this idea. Returns list of IDs."""
    ideas_by_id = {i["id"]: i for i in all_ideas}
    chain = [idea_id]
    current = ideas_by_id.get(idea_id)
    seen = {idea_id}
    while current and current.get("parent_id"):
        parent_id = current["parent_id"]
        if parent_id in seen:  # cycle protection
            break
        chain.insert(0, parent_id)
        seen.add(parent_id)
        current = ideas_by_id.get(parent_id)
    return chain if len(chain) > 1 else []


# -- CLI --

def _setup_extra_parsers(sub):
    # Add extra args to the 'read' parser (already created by make_cli)
    read_parser = sub.choices.get("read") or sub._name_parser_map.get("read")
    if read_parser:
        read_parser.add_argument("--status",
                                 choices=sorted(VALID_STATUSES),
                                 help="Filter by status")
        read_parser.add_argument("--category",
                                 choices=sorted(VALID_CATEGORIES),
                                 help="Filter by category")
        read_parser.add_argument("--parent",
                                 help="Filter by parent ID (or 'root' for top-level)")

    p = sub.add_parser("show", help="Show full idea details")
    p.add_argument("project")
    p.add_argument("idea_id")

    p = sub.add_parser("commit", help="Mark APPROVED idea as COMMITTED")
    p.add_argument("project")
    p.add_argument("idea_id")


def main():
    make_cli(
        _mod,
        extra_commands={
            "show": cmd_show,
            "commit": cmd_commit,
        },
        setup_extra_parsers=_setup_extra_parsers,
        description="Forge Ideas -- staging area for proposals and plans",
    )


if __name__ == "__main__":
    main()
