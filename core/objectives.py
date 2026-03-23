"""
Objectives — business goals with measurable key results.

Objectives sit ABOVE ideas in the Forge hierarchy. They answer "what do we
want to achieve and how will we measure it?" Ideas then represent proposals
for HOW to achieve objectives.

Hierarchy:
    Objective (north star)
        └── Key Results (measurable targets)
              └── Ideas (linked via advances_key_results)
                    └── Tasks (implementation)

Objectives can be:
- project-scoped: live in forge_output/{project}/objectives.json
- cross-project: live in forge_output/_objectives/objectives.json

Key Results have:
- metric: what we measure
- baseline: where we started
- target: where we want to be
- current: where we are now (updated manually)

Usage:
    python -m core.objectives <command> <project> [options]

Commands:
    add      {project} --data '{json}'         Add objectives with key results
    read     {project} [--status X]            Read objectives
    show     {project} {objective_id}          Show details + coverage + progress
    update   {project} --data '{json}'         Update objective/KR fields
    status   {project}                         Coverage dashboard
    contract {name}                            Print contract spec
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from entity_base import EntityModule, make_cli
from errors import EntityNotFound, ValidationError
from models import Objective
from storage import JSONFileStorage, load_json_data, now_iso
from trace import trace_cmd


# -- Constants --

VALID_STATUSES = {"ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"}

VALID_TRANSITIONS = {
    "ACTIVE": {"ACHIEVED", "ABANDONED", "PAUSED"},
    "PAUSED": {"ACTIVE", "ABANDONED"},
    "ACHIEVED": {"ACTIVE"},      # reopen if KRs regress
    "ABANDONED": {"ACTIVE"},     # reopen if circumstances change
}

KR_STATUSES = {"NOT_STARTED", "IN_PROGRESS", "ACHIEVED"}


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["title", "description", "key_results"],
        "optional": ["appetite", "scope", "assumptions", "tags",
                      "scopes", "derived_guidelines", "knowledge_ids",
                      "guideline_ids", "relations"],
        "enums": {
            "appetite": {"small", "medium", "large"},
            "scope": {"project", "cross-project"},
        },
        "types": {
            "key_results": list,
            "assumptions": list,
            "tags": list,
            "scopes": list,
            "derived_guidelines": list,
            "knowledge_ids": list,
            "guideline_ids": list,
            "relations": list,
        },
        "invariants": [
            (lambda item, i: len(item.get("key_results", [])) >= 1,
             "At least one key_result is required"),
            (lambda item, i: all(
                isinstance(kr, dict) and (
                    (kr.get("metric") and kr.get("target") is not None)
                    or kr.get("description")
                )
                for kr in item.get("key_results", [])
            ), "Each key_result must have either ('metric' + 'target') or 'description' (or both)"),
            (lambda item, i: all(
                isinstance(r, dict)
                and r.get("type") in ("depends_on", "related_to", "supersedes", "duplicates")
                and isinstance(r.get("target_id"), str)
                for r in item.get("relations", [])
            ), "Each relation must have 'type' (depends_on|related_to|supersedes|duplicates) and 'target_id' (O-NNN)"),
        ],
        "invariant_texts": [
            "title: concise name for the objective (e.g., 'Reduce API response time')",
            "description: why this matters, who benefits, business context",
            "key_results: array of outcomes (at least 1). Two styles supported:",
            "  Numeric KR: {metric, baseline, target, current} — progress tracked as percentage",
            "  Descriptive KR: {description} — progress tracked via status badge (NOT_STARTED/IN_PROGRESS/ACHIEVED)",
            "  Both styles can be combined: {metric, target, description}",
            "  - metric: what we measure (e.g., 'p95 response time in ms') — required for numeric KRs",
            "  - baseline: starting value (number, default 0)",
            "  - target: goal value (number, required for numeric KRs)",
            "  - current: current value (number, default = baseline)",
            "  - description: qualitative outcome description — required for descriptive KRs",
            "  - measurement: how to measure current value — 'command' | 'test' | 'manual' (optional, default: manual)",
            "  - command: shell command that outputs a single number to stdout (required if measurement='command')",
            "  - test_path: pytest path to run (required if measurement='test')",
            "  - check: human-readable verification instructions (for measurement='manual')",
            "  - direction: 'up' (higher=better) or 'down' (lower=better) — auto-inferred from baseline vs target if omitted",
            "appetite: effort budget — small (days), medium (weeks), large (months). From Shape Up.",
            "scope: 'project' (single project) or 'cross-project' (spans multiple projects)",
            "assumptions: list of strings — explicit assumptions that must hold for this objective to make sense. "
            "Each assumption is a hypothesis to validate. (From Theory of Change.)",
            "tags: searchable keywords",
            "scopes: list of guideline scopes this objective relates to (e.g., ['backend', 'performance']). "
            "Ideas/tasks linked to this objective can inherit these scopes for guideline loading.",
            "derived_guidelines: list of guideline IDs that were created BECAUSE of this objective (e.g., ['G-010']). "
            "Outbound link — 'these guidelines exist because of this objective'. NOT 'these guidelines apply to this objective'.",
            "knowledge_ids: list of Knowledge IDs (K-001, etc.) that provide context for this objective.",
            "guideline_ids: list of guideline IDs explicitly assigned to this objective (e.g., ['G-001', 'G-005']). "
            "Inbound link — guidelines that apply to this objective beyond scope-based auto-loading.",
            "relations: list of typed relations to other objectives. Each: {type, target_id, notes?}. "
            "Types: depends_on, related_to, supersedes, duplicates. target_id is O-NNN format.",
        ],
        "example": [
            {
                "title": "Reduce API response time",
                "description": "Users complain about slow API. Reducing p95 below 200ms will improve retention and reduce support tickets.",
                "key_results": [
                    {"metric": "p95 response time (ms)", "baseline": 850, "target": 200},
                    {"metric": "timeout errors per day", "baseline": 47, "target": 0},
                    {"description": "All critical endpoints have caching strategy documented"},
                ],
                "appetite": "medium",
                "scope": "project",
                "assumptions": [
                    "Slowness is server-side, not client network",
                    "Redis caching will address the main bottleneck",
                ],
                "tags": ["performance", "api"],
                "scopes": ["backend", "performance"],
                "derived_guidelines": ["G-010"],
                "guideline_ids": ["G-001", "G-005"],
                "relations": [
                    {"type": "related_to", "target_id": "O-002", "notes": "Shared infrastructure concern"},
                ],
            }
        ],
    },
    "update": {
        "required": ["id"],
        "optional": ["title", "description", "status", "appetite",
                      "assumptions", "tags", "key_results",
                      "scopes", "derived_guidelines", "knowledge_ids",
                      "guideline_ids", "relations"],
        "enums": {
            "status": {"ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"},
            "appetite": {"small", "medium", "large"},
        },
        "types": {
            "assumptions": list,
            "tags": list,
            "key_results": list,
            "scopes": list,
            "derived_guidelines": list,
            "knowledge_ids": list,
            "guideline_ids": list,
            "relations": list,
        },
        "invariant_texts": [
            "id: existing objective ID (O-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "status: ACTIVE (working on it), ACHIEVED (all KRs met), ABANDONED (no longer relevant), PAUSED (on hold)",
            "key_results: update specific KRs by including their id (KR-1, etc.) with new values. "
            "Only update 'current' for progress tracking. Include {id, current} at minimum. "
            "For descriptive KRs, update 'status' (NOT_STARTED/IN_PROGRESS/ACHIEVED).",
            "assumptions: replaces the full list (not append-merged)",
            "guideline_ids: replaces the full list of explicitly assigned guidelines",
            "relations: replaces the full list of objective relations",
        ],
        "example": [
            {"id": "O-001", "key_results": [
                {"id": "KR-1", "current": 320},
                {"id": "KR-2", "current": 12},
            ]},
            {"id": "O-002", "status": "ACHIEVED"},
        ],
    },
}


# -- Module --

class Objectives(EntityModule):
    entity_type = "objectives"
    list_key = "objectives"
    id_prefix = "O"
    display_name = "Objectives"
    dedup_keys = ()
    contracts = CONTRACTS
    model_class = Objective

    def build_entity(self, input_item, entity_id, timestamp, args):
        # Build key results with IDs
        key_results = []
        for kr_idx, kr in enumerate(input_item["key_results"], 1):
            kr_data = {"id": f"KR-{kr_idx}"}
            # Numeric KR fields (metric + target)
            if kr.get("metric"):
                kr_data["metric"] = kr["metric"]
                kr_data["baseline"] = kr.get("baseline", 0)
                kr_data["target"] = kr["target"]
                kr_data["current"] = kr.get("current", kr.get("baseline", 0))
            # Descriptive KR field
            if kr.get("description"):
                kr_data["description"] = kr["description"]
                if "metric" not in kr_data:
                    kr_data["status"] = kr.get("status", "NOT_STARTED")
            # Measurement fields
            if kr.get("measurement"):
                kr_data["measurement"] = kr["measurement"]
                for f in ("command", "test_path", "check", "direction"):
                    if kr.get(f):
                        kr_data[f] = kr[f]
                # Auto-infer direction
                if "direction" not in kr_data and kr_data.get("target") is not None and kr_data.get("baseline") is not None:
                    kr_data["direction"] = "up" if kr_data["target"] > kr_data["baseline"] else "down"
            key_results.append(kr_data)

        return {
            "id": entity_id,
            "title": input_item["title"],
            "description": input_item["description"],
            "key_results": key_results,
            "appetite": input_item.get("appetite", "medium"),
            "scope": input_item.get("scope", "project"),
            "assumptions": input_item.get("assumptions", []),
            "tags": input_item.get("tags", []),
            "scopes": input_item.get("scopes", []),
            "derived_guidelines": input_item.get("derived_guidelines", []),
            "knowledge_ids": input_item.get("knowledge_ids", []),
            "guideline_ids": input_item.get("guideline_ids", []),
            "relations": input_item.get("relations", []),
            "status": "ACTIVE",
            "created": timestamp,
            "updated": timestamp,
        }

    def print_add_summary(self, project, data, added, skipped):
        print(f"Objectives saved: {project}")
        if added:
            print(f"  Added: {len(added)} ({', '.join(added)})")
        for obj_id in added:
            obj = next(o for o in data["objectives"] if o["id"] == obj_id)
            print(f"  {obj_id}: {obj['title']}")
            for kr in obj["key_results"]:
                if kr.get("metric"):
                    direction = "\u2191" if kr["target"] > kr["baseline"] else "\u2193"
                    print(f"    {kr['id']}: {kr['metric']} \u2014 {kr['baseline']} {direction} {kr['target']}")
                else:
                    print(f"    {kr['id']}: {kr.get('description', '(descriptive)')}")

    def apply_filters(self, items, args):
        if getattr(args, 'status', None):
            items = [o for o in items if o.get("status") == args.status]
        return items

    def render_list(self, items, args):
        print(f"## Objectives: {args.project}")
        if getattr(args, 'status', None):
            print(f"Filter: status={args.status}")
        print(f"Count: {len(items)}")
        print()

        if not items:
            print("(none)")
            return

        print("| ID | Status | Appetite | Title | KR Progress |")
        print("|----|--------|----------|-------|-------------|")
        for o in items:
            kr_summary = _kr_progress_summary(o.get("key_results", []))
            title = o.get("title", "")[:35]
            print(f"| {o['id']} | {o.get('status', '')} | {o.get('appetite', '')} | {title} | {kr_summary} |")

    def cmd_update(self, args):
        """Update objective fields and KR progress."""
        try:
            updates = load_json_data(args.data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

        if not isinstance(updates, list):
            updates = [updates]

        from contracts import validate_contract
        errors = validate_contract(CONTRACTS["update"], updates)
        if errors:
            detail = "; ".join(errors[:10])
            raise ValidationError(f"{len(errors)} validation issues: {detail}")

        data = self.load(args.project)
        timestamp = now_iso()

        updated = []
        for u in updates:
            obj = self.find_by_id(data, u["id"])
            if obj is None:
                print(f"  WARNING: Objective {u['id']} not found, skipping", file=sys.stderr)
                continue

            # Simple field updates
            for field in ["title", "description", "appetite", "assumptions", "tags",
                           "scopes", "derived_guidelines", "knowledge_ids",
                           "guideline_ids", "relations"]:
                if field in u:
                    obj[field] = u[field]

            # Status update with transition validation and lifecycle warning (F-004)
            if "status" in u:
                new_status = u["status"]
                old_status = obj.get("status", "ACTIVE")
                valid_next = VALID_TRANSITIONS.get(old_status, set())
                if new_status not in valid_next:
                    print(f"  WARNING: Invalid transition {old_status}->{new_status} for {u['id']}. "
                          f"Valid: {', '.join(sorted(valid_next)) or 'none'}",
                          file=sys.stderr)
                    continue
                obj["status"] = new_status
                # Lifecycle warning: check derived guidelines when objective ends
                if new_status in ("ACHIEVED", "ABANDONED") and old_status == "ACTIVE":
                    derived = obj.get("derived_guidelines", [])
                    if derived:
                        print(f"\n  NOTE: {u['id']} has derived guidelines: {', '.join(derived)}")
                        if new_status == "ACHIEVED":
                            print(f"  Review if these guidelines should become permanent standards")
                            print(f"  or be deprecated now that the objective is achieved.")
                        else:
                            print(f"  Review if these guidelines are still relevant")
                            print(f"  now that the objective is abandoned.")

            # Key result updates (merge by KR id)
            if "key_results" in u:
                existing_krs = {kr["id"]: kr for kr in obj.get("key_results", [])}
                for kr_update in u["key_results"]:
                    kr_id = kr_update.get("id")
                    if kr_id and kr_id in existing_krs:
                        for field in ["current", "metric", "baseline", "target",
                                      "description", "status"]:
                            if field in kr_update:
                                existing_krs[kr_id][field] = kr_update[field]
                    else:
                        print(f"  WARNING: KR '{kr_id}' not found in {u['id']}, skipping",
                              file=sys.stderr)

            obj["updated"] = timestamp
            updated.append(u["id"])

        self.save(args.project, data)
        trace_cmd(args.project, "objectives", "update", updated=updated)

        print(f"Updated {len(updated)} objectives: {args.project}")
        for obj_id in updated:
            obj = next(o for o in data["objectives"] if o["id"] == obj_id)
            print(f"  {obj_id}: {obj['title']} ({obj['status']})")
            for kr in obj.get("key_results", []):
                if kr.get("metric"):
                    pct = _kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
                    print(f"    {kr['id']}: {kr['metric']} \u2014 {kr.get('current', '?')}/{kr['target']} ({pct}%)")
                else:
                    print(f"    {kr['id']}: {kr.get('description', '(descriptive)')} [{kr.get('status', 'NOT_STARTED')}]")


_mod = Objectives()

# Public API used by other modules
load_or_create = _mod.load
save_json = _mod.save
find_objective = _mod.find_by_id


# -- Custom commands --

def cmd_show(args):
    """Show full details for a single objective with coverage analysis."""
    data = _mod.load(args.project)
    obj = _mod.find_by_id(data, args.objective_id)
    if not obj:
        raise EntityNotFound(f"Objective '{args.objective_id}' not found.")

    print(f"## Objective {obj['id']}: {obj['title']}")
    print()
    print(f"- **Status**: {obj['status']}")
    print(f"- **Appetite**: {obj.get('appetite', 'medium')}")
    print(f"- **Scope**: {obj.get('scope', 'project')}")
    print(f"- **Created**: {obj.get('created', '')}")
    if obj.get("tags"):
        print(f"- **Tags**: {', '.join(obj['tags'])}")
    if obj.get("scopes"):
        print(f"- **Scopes**: {', '.join(obj['scopes'])}")
    if obj.get("derived_guidelines"):
        print(f"- **Derived Guidelines**: {', '.join(obj['derived_guidelines'])}")
    if obj.get("knowledge_ids"):
        print(f"- **Knowledge**: {', '.join(obj['knowledge_ids'])}")
    if obj.get("guideline_ids"):
        print(f"- **Assigned Guidelines**: {', '.join(obj['guideline_ids'])}")
    if obj.get("relations"):
        print(f"- **Relations**: {len(obj['relations'])} links")
    print()
    print("### Description")
    print(obj.get("description", ""))
    print()

    # Key Results with progress bars
    print("### Key Results")
    print()
    for kr in obj.get("key_results", []):
        if kr.get("metric"):
            baseline = kr.get("baseline", 0)
            target = kr["target"]
            current = kr.get("current", baseline)
            pct = _kr_percentage(baseline, target, current)
            bar = _progress_bar(pct)
            direction = "\u2193" if target < baseline else "\u2191"
            print(f"**{kr['id']}**: {kr['metric']}")
            print(f"  {baseline} {direction} **{current}** \u2192 {target}  {bar} {pct}%")
        else:
            status = kr.get("status", "NOT_STARTED")
            print(f"**{kr['id']}**: {kr.get('description', '(descriptive)')}")
            print(f"  Status: [{status}]")
        print()

    # Assumptions
    if obj.get("assumptions"):
        print("### Assumptions")
        for a in obj["assumptions"]:
            print(f"- {a}")
        print()

    # Coverage: find linked ideas
    _s = JSONFileStorage()
    linked_ideas = []
    if _s.exists(args.project, 'ideas'):
        ideas_data = _s.load_data(args.project, 'ideas')
        for idea in ideas_data.get("ideas", []):
            advances = idea.get("advances_key_results", [])
            if any(kr_ref.startswith(obj["id"]) or kr_ref in _kr_full_ids(obj)
                   for kr_ref in advances):
                linked_ideas.append(idea)

    if linked_ideas:
        print(f"### Linked Ideas ({len(linked_ideas)})")
        print()
        print("| Idea | Status | Advances KRs | Title |")
        print("|------|--------|-------------|-------|")
        for idea in linked_ideas:
            krs = ", ".join(idea.get("advances_key_results", []))
            print(f"| {idea['id']} | {idea['status']} | {krs} | {idea['title'][:30]} |")
        print()

    # Coverage analysis: which KRs have linked ideas?
    kr_ids = _kr_full_ids(obj)
    covered_krs = set()
    for idea in linked_ideas:
        for kr_ref in idea.get("advances_key_results", []):
            if kr_ref in kr_ids:
                covered_krs.add(kr_ref)

    total_krs = len(kr_ids)
    covered = len(covered_krs)
    uncovered = kr_ids - covered_krs

    print("### Coverage")
    print(f"- **Planning coverage**: {covered}/{total_krs} KRs have linked Ideas")
    if uncovered:
        print(f"- **Uncovered KRs**: {', '.join(sorted(uncovered))}")
        print("  These KRs have no Ideas addressing them yet.")

    # Task progress for linked ideas
    if _s.exists(args.project, 'tracker') and linked_ideas:
        tracker = _s.load_data(args.project, 'tracker')
        tasks = tracker.get("tasks", [])
        idea_ids = {i["id"] for i in linked_ideas}
        related_tasks = [t for t in tasks if t.get("origin") in idea_ids]
        if related_tasks:
            done = sum(1 for t in related_tasks if t.get("status") == "DONE")
            total = len(related_tasks)
            print(f"- **Execution progress**: {done}/{total} tasks DONE ({_pct(done, total)}%)")

    print()

    # Decisions affecting this objective (from deferred items with affects=[O-xxx])
    if _s.exists(args.project, 'decisions'):
        dec_data = _s.load_data(args.project, 'decisions')
        affecting = [d for d in dec_data.get("decisions", [])
                     if obj["id"] in (d.get("affects") or [])]
        if affecting:
            open_count = sum(1 for d in affecting if d.get("status") == "OPEN")
            print(f"### Decisions Affecting This Objective ({len(affecting)}, {open_count} OPEN)")
            print()
            for d in affecting:
                status_icon = "\U0001f534" if d.get("status") == "OPEN" else "\U0001f7e2"
                print(f"- {status_icon} **{d['id']}** ({d.get('status', '')}): {d.get('issue', '')}")
                if d.get("recommendation"):
                    print(f"  \u2192 {d['recommendation']}")
                if d.get("task_id"):
                    print(f"  Source: {d['task_id']}")
            print()

    # Relations
    if obj.get("relations"):
        print("### Relations")
        for rel in obj["relations"]:
            notes = f" \u2014 {rel['notes']}" if rel.get("notes") else ""
            print(f"- [{rel['type']}] \u2192 {rel['target_id']}{notes}")
        print()

    # Overall KR progress
    numeric_krs = [kr for kr in obj.get("key_results", []) if kr.get("metric") and kr.get("target") is not None]
    kr_pcts = [_kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
               for kr in numeric_krs]
    avg_pct = sum(kr_pcts) // len(kr_pcts) if kr_pcts else 0
    print(f"- **Outcome progress**: {avg_pct}% average across KRs")


def cmd_status(args):
    """Coverage dashboard across all objectives."""
    storage = JSONFileStorage()
    if not storage.exists(args.project, 'objectives'):
        print(f"No objectives for '{args.project}' yet.")
        return

    data = storage.load_data(args.project, 'objectives')
    objectives = data.get("objectives", [])

    if not objectives:
        print("No objectives defined.")
        return

    # Load ideas for coverage
    _s = JSONFileStorage()
    all_ideas = []
    if _s.exists(args.project, 'ideas'):
        ideas_data = _s.load_data(args.project, 'ideas')
        all_ideas = ideas_data.get("ideas", [])

    # Load tasks for execution progress
    all_tasks = []
    if _s.exists(args.project, 'tracker'):
        tracker = _s.load_data(args.project, 'tracker')
        all_tasks = tracker.get("tasks", [])

    print(f"## Objective Dashboard: {args.project}")
    print()

    for obj in objectives:
        if obj.get("status") in ("ABANDONED",):
            continue

        print(f"### {obj['id']}: {obj['title']} [{obj['status']}]")
        if obj.get("appetite"):
            print(f"Appetite: {obj['appetite']}")
        print()

        # KR progress
        kr_ids = _kr_full_ids(obj)
        covered_krs = set()
        idea_ids_for_obj = set()

        for idea in all_ideas:
            advances = idea.get("advances_key_results", [])
            matching = [kr for kr in advances if kr in kr_ids]
            if matching:
                covered_krs.update(matching)
                idea_ids_for_obj.add(idea["id"])

        for kr in obj.get("key_results", []):
            full_id = f"{obj['id']}/{kr['id']}"
            covered_mark = "+" if full_id in covered_krs else "-"
            if kr.get("metric"):
                pct = _kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
                bar = _progress_bar(pct)
                print(f"  [{covered_mark}] {kr['id']}: {kr['metric']} {bar} {pct}%  ({kr.get('current', '?')}/{kr['target']})")
            else:
                status = kr.get("status", "NOT_STARTED")
                desc = kr.get("description", "(descriptive)")[:40]
                print(f"  [{covered_mark}] {kr['id']}: {desc} [{status}]")

        # Task progress
        related_tasks = [t for t in all_tasks if t.get("origin") in idea_ids_for_obj]
        if related_tasks:
            done = sum(1 for t in related_tasks if t.get("status") == "DONE")
            total = len(related_tasks)
            print(f"  Tasks: {done}/{total} done ({_pct(done, total)}%)")

        # Summary line
        total_krs = len(kr_ids)
        covered_count = len(covered_krs)
        numeric_krs = [kr for kr in obj.get("key_results", []) if kr.get("metric") and kr.get("target") is not None]
        kr_pcts = [_kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
                   for kr in numeric_krs]
        avg_pct = sum(kr_pcts) // len(kr_pcts) if kr_pcts else 0
        print(f"  Planning: {covered_count}/{total_krs} KRs covered | Outcome: {avg_pct}% avg")
        print()


# -- Helpers --

def _kr_full_ids(obj: dict) -> set:
    """Get full KR IDs like 'O-001/KR-1' for an objective."""
    return {f"{obj['id']}/{kr['id']}" for kr in obj.get("key_results", [])}


def _kr_percentage(baseline, target, current) -> int:
    """Calculate KR progress percentage (0-100)."""
    try:
        baseline = float(baseline)
        target = float(target)
        current = float(current)
    except (TypeError, ValueError):
        return 0

    total_delta = target - baseline
    if total_delta == 0:
        return 100 if current == target else 0

    current_delta = current - baseline
    pct = (current_delta / total_delta) * 100
    return max(0, min(100, int(pct)))


def _kr_progress_summary(key_results: list) -> str:
    """One-line summary of KR progress."""
    if not key_results:
        return "\u2014"
    numeric_krs = [kr for kr in key_results if kr.get("metric") and kr.get("target") is not None]
    descriptive_krs = [kr for kr in key_results if not (kr.get("metric") and kr.get("target") is not None)]
    parts = []
    if numeric_krs:
        pcts = [_kr_percentage(kr.get("baseline", 0), kr["target"],
                               kr.get("current", kr.get("baseline", 0)))
                for kr in numeric_krs]
        avg = sum(pcts) // len(pcts)
        parts.append(f"{avg}%")
    if descriptive_krs:
        achieved = sum(1 for kr in descriptive_krs if kr.get("status") == "ACHIEVED")
        parts.append(f"{achieved}/{len(descriptive_krs)} desc")
    total = len(key_results)
    return f"{', '.join(parts)} ({total} KRs)"


def _progress_bar(pct: int, width: int = 10) -> str:
    """Simple text progress bar."""
    filled = int(width * pct / 100)
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}]"


def _pct(done: int, total: int) -> int:
    return int(done / total * 100) if total > 0 else 0


# -- Measure --

def cmd_measure(args):
    """Run measurement commands for KRs in an objective."""
    import subprocess as _sp
    from pipeline_common import get_project_dir

    data = _mod.load(args.project)
    obj = _mod.find_by_id(data, args.objective_id)
    if not obj:
        raise EntityNotFound(f"Objective '{args.objective_id}' not found.")

    project_dir = get_project_dir(args.project)
    kr_filter = getattr(args, 'kr', None)
    changed = False

    print(f"## Measuring KRs: {obj['id']} — {obj['title']}")
    print()

    for kr in obj.get("key_results", []):
        if kr_filter and kr["id"] != kr_filter:
            continue

        measurement = kr.get("measurement")
        if not measurement or measurement == "manual":
            if measurement == "manual" and kr.get("check"):
                print(f"  {kr['id']}: [manual] {kr.get('check', '')}")
            elif kr.get("target") is not None:
                print(f"  {kr['id']}: {kr.get('current', '?')}/{kr['target']} — no measurement command")
            continue

        if measurement == "command":
            command = kr.get("command", "")
            if not command:
                print(f"  {kr['id']}: measurement=command but no command specified")
                continue
            print(f"  {kr['id']}: running `{command}` ...", end=" ")
            try:
                result = _sp.run(command, shell=True, capture_output=True,
                               text=True, encoding="utf-8", timeout=120,
                               cwd=project_dir)
                output = (result.stdout or "").strip()
                try:
                    value = float(output)
                except ValueError:
                    print(f"FAIL — output is not a number: '{output[:60]}'")
                    continue

                old = kr.get("current", kr.get("baseline", 0))
                kr["current"] = value
                kr["last_measured_at"] = now_iso()
                history = kr.get("measurement_history", [])
                history.append({"value": value, "timestamp": now_iso(), "source": "cmd_measure"})
                kr["measurement_history"] = history[-20:]

                # Check if target met
                target = kr.get("target")
                direction = kr.get("direction", "up")
                met = False
                if target is not None:
                    met = (value <= target) if direction == "down" else (value >= target)

                pct = _kr_percentage(kr.get("baseline", 0), target, value) if target else 0
                status_str = "TARGET MET" if met else f"{pct}%"
                print(f"{old} → {value} (target: {target}, {status_str})")

                if met and kr.get("status") != "ACHIEVED":
                    kr["status"] = "ACHIEVED"
                    kr["achieved_at"] = now_iso()
                    print(f"    → KR ACHIEVED!")

                changed = True
                trace_cmd(args.project, "objectives", "measure_kr",
                         objective=obj["id"], kr=kr["id"],
                         old=old, new=value, target=target, met=met)

            except _sp.TimeoutExpired:
                print(f"TIMEOUT (120s)")

        elif measurement == "test":
            test_path = kr.get("test_path", "")
            if not test_path:
                print(f"  {kr['id']}: measurement=test but no test_path specified")
                continue
            cmd_str = f"pytest {test_path} -x -q"
            print(f"  {kr['id']}: running `{cmd_str}` ...", end=" ")
            try:
                result = _sp.run(cmd_str, shell=True, capture_output=True,
                               text=True, encoding="utf-8", timeout=120,
                               cwd=project_dir)
                passed = result.returncode == 0
                status = "PASS" if passed else "FAIL"
                print(status)
                if passed and kr.get("status") != "ACHIEVED":
                    kr["status"] = "ACHIEVED"
                    kr["achieved_at"] = now_iso()
                    print(f"    → KR ACHIEVED!")
                    changed = True
                trace_cmd(args.project, "objectives", "measure_kr",
                         objective=obj["id"], kr=kr["id"], test=test_path, passed=passed)
            except _sp.TimeoutExpired:
                print(f"TIMEOUT (120s)")

    if changed:
        obj["updated"] = now_iso()
        _mod.save(args.project, data)
        print(f"\nProgress saved.")


def validate_analysis_completeness(project: str) -> tuple:
    """Validate that analysis produced all required artifacts (Contract C2).

    Returns (verdict: "PASS"|"WARN"|"FAIL"|"SKIP", details: dict).
    SKIP = no source documents (standalone project, analysis not required).
    FAIL = analysis incomplete — hard gate should block planning.
    """
    from storage import JSONFileStorage
    _s = JSONFileStorage()

    # Check if source documents exist (analysis only required when docs were ingested)
    has_source_docs = False
    if _s.exists(project, 'knowledge'):
        k_data = _s.load_data(project, 'knowledge')
        has_source_docs = any(
            k.get("category") == "source-document"
            for k in k_data.get("knowledge", [])
            if k.get("status", "ACTIVE") in ("ACTIVE", "DRAFT")
        )

    if not has_source_docs:
        return "SKIP", {"reason": "no source documents — analysis not required"}

    errors = []
    warnings = []

    # 1. Check objectives exist
    if not _s.exists(project, 'objectives'):
        errors.append("No objectives.json — run /analyze to create objectives from ingested requirements.")
        return "FAIL", {"errors": errors, "warnings": warnings,
                        "active_objectives": 0, "krs_without_measurement": [],
                        "orphaned_requirements": []}

    obj_data = _s.load_data(project, 'objectives')
    active_objs = [o for o in obj_data.get("objectives", []) if o.get("status") == "ACTIVE"]

    if not active_objs:
        errors.append("No ACTIVE objectives. Run /analyze to create objectives from ingested requirements.")
        return "FAIL", {"errors": errors, "warnings": warnings,
                        "active_objectives": 0, "krs_without_measurement": [],
                        "orphaned_requirements": []}

    # 2. Check every KR has measurement field
    krs_without_measurement = []
    for obj in active_objs:
        for kr in obj.get("key_results", []):
            if not kr.get("measurement"):
                krs_without_measurement.append(
                    f"{obj['id']}/{kr['id']}: {kr.get('metric') or kr.get('description', '?')[:50]}"
                )

    if krs_without_measurement:
        errors.append(
            f"{len(krs_without_measurement)} KR(s) without measurement method. "
            f"KR auto-update will not work. Fix via: "
            f"python -m core.objectives update {{project}} --data '[{{\"id\": \"O-NNN\", ...}}]'"
        )

    # 3. Check orphaned requirements (K-NNN category=requirement without objective link)
    orphaned_requirements = []
    if _s.exists(project, 'knowledge'):
        k_data = _s.load_data(project, 'knowledge')
        requirements = [k for k in k_data.get("knowledge", [])
                        if k.get("category") == "requirement"
                        and k.get("status", "ACTIVE") in ("ACTIVE", "DRAFT")]
        for req in requirements:
            has_obj_link = any(
                le.get("entity_type") == "objective"
                for le in req.get("linked_entities", [])
            )
            if not has_obj_link:
                orphaned_requirements.append(f"{req['id']}: {req.get('title', '?')[:60]}")

    if orphaned_requirements:
        warnings.append(
            f"{len(orphaned_requirements)} requirement(s) not linked to any objective. "
            f"Link via: python -m core.knowledge link {{project}} --data '[...]'"
        )

    # Determine verdict
    if errors:
        verdict = "FAIL"
    elif warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return verdict, {
        "errors": errors,
        "warnings": warnings,
        "active_objectives": len(active_objs),
        "krs_without_measurement": krs_without_measurement,
        "orphaned_requirements": orphaned_requirements,
    }


def cmd_verify(args):
    """CLI command: verify analysis completeness (Contract C2)."""
    project = args.project
    verdict, details = validate_analysis_completeness(project)

    print(f"## Analysis Verification: {project}")
    print(f"Verdict: {verdict}")
    print()

    if verdict == "SKIP":
        print(f"  {details.get('reason', 'Analysis not required.')}")
        return

    print(f"  Active objectives: {details.get('active_objectives', 0)}")

    if details.get("krs_without_measurement"):
        print(f"\n  KRs without measurement ({len(details['krs_without_measurement'])}):")
        for kr in details["krs_without_measurement"]:
            print(f"    [-] {kr}")

    if details.get("orphaned_requirements"):
        print(f"\n  Orphaned requirements ({len(details['orphaned_requirements'])}):")
        for req in details["orphaned_requirements"]:
            print(f"    [-] {req}")

    if details.get("errors"):
        print(f"\n  ERRORS (must fix before /plan):")
        for e in details["errors"]:
            print(f"    ! {e}")

    if details.get("warnings"):
        print(f"\n  WARNINGS:")
        for w in details["warnings"]:
            print(f"    ? {w}")

    print()
    if verdict == "PASS":
        print("  Analysis complete. Ready for /plan --objective O-NNN.")
    elif verdict == "WARN":
        print("  Analysis has minor gaps. /plan can proceed but review warnings.")
    else:
        print("  Analysis INCOMPLETE. Fix errors before running /plan.")
        import sys
        sys.exit(1)


# -- CLI --

def _setup_extra_parsers(sub):
    read_parser = sub.choices["read"]
    read_parser.add_argument("--status", choices=sorted(VALID_STATUSES))

    p = sub.add_parser("show", help="Show objective details + coverage")
    p.add_argument("project")
    p.add_argument("objective_id")

    p = sub.add_parser("status", help="Coverage dashboard")
    p.add_argument("project")

    p = sub.add_parser("verify", help="Verify analysis completeness (Contract C2)")
    p.add_argument("project")

    p = sub.add_parser("measure", help="Run KR measurement commands")
    p.add_argument("project")
    p.add_argument("objective_id")
    p.add_argument("--kr", help="Specific KR ID to measure (e.g. KR-1)")


def main():
    make_cli(
        _mod,
        extra_commands={
            "show": cmd_show,
            "status": cmd_status,
            "measure": cmd_measure,
            "verify": cmd_verify,
        },
        setup_extra_parsers=_setup_extra_parsers,
        description="Forge Objectives \u2014 business goals with measurable key results",
    )


if __name__ == "__main__":
    main()
