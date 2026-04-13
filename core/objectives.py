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
    add              {project} --data '{json}'         Add objectives with key results
    read             {project} [--status X]            Read objectives
    show             {project} {objective_id}          Show details + coverage + progress
    update           {project} --data '{json}'         Update objective/KR fields
    status           {project}                         Coverage dashboard
    derive-guideline {project} {obj_id} --data '{json}'  Create guideline linked to objective
    contract         {name}                            Print contract spec
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

def objectives_path(project: str) -> Path:
    return Path("forge_output") / project / "objectives.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_or_create(project: str) -> dict:
    path = objectives_path(project)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "project": project,
        "updated": now_iso(),
        "objectives": [],
    }


def save_json(project: str, data: dict):
    path = objectives_path(project)
    data["updated"] = now_iso()
    atomic_write_json(path, data)


def find_objective(data: dict, obj_id: str) -> dict:
    """Find objective by ID. Exits with error if not found."""
    for obj in data.get("objectives", []):
        if obj["id"] == obj_id:
            return obj
    print(f"ERROR: Objective '{obj_id}' not found.", file=sys.stderr)
    sys.exit(1)


# -- Contracts --

CONTRACTS = {
    "add": {
        "required": ["title", "description", "key_results"],
        "optional": ["appetite", "scope", "assumptions", "tags",
                      "scopes", "derived_guidelines"],
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
        },
        "invariants": [
            (lambda item, i: len(item.get("key_results", [])) >= 1,
             "At least one key_result is required"),
            (lambda item, i: all(
                isinstance(kr, dict) and kr.get("metric") and kr.get("target") is not None
                for kr in item.get("key_results", [])
            ), "Each key_result must have 'metric' (string) and 'target' (number)"),
        ],
        "invariant_texts": [
            "title: concise name for the objective (e.g., 'Reduce API response time')",
            "description: why this matters, who benefits, business context",
            "key_results: array of measurable outcomes (at least 1). Each: {metric, baseline, target, current}",
            "  - metric: what we measure (e.g., 'p95 response time in ms')",
            "  - baseline: starting value (number, default 0)",
            "  - target: goal value (number, required)",
            "  - current: current value (number, default = baseline)",
            "appetite: effort budget — small (days), medium (weeks), large (months). From Shape Up.",
            "scope: 'project' (single project) or 'cross-project' (spans multiple projects)",
            "assumptions: list of strings — explicit assumptions that must hold for this objective to make sense. "
            "Each assumption is a hypothesis to validate. (From Theory of Change.)",
            "tags: searchable keywords",
            "scopes: list of guideline scopes this objective relates to (e.g., ['backend', 'performance']). "
            "Ideas/tasks linked to this objective can inherit these scopes for guideline loading.",
            "derived_guidelines: list of guideline IDs that were created BECAUSE of this objective (e.g., ['G-010']). "
            "Outbound link — 'these guidelines exist because of this objective'. NOT 'these guidelines apply to this objective'.",
        ],
        "example": [
            {
                "title": "Reduce API response time",
                "description": "Users complain about slow API. Reducing p95 below 200ms will improve retention and reduce support tickets.",
                "key_results": [
                    {"metric": "p95 response time (ms)", "baseline": 850, "target": 200},
                    {"metric": "timeout errors per day", "baseline": 47, "target": 0},
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
            }
        ],
    },
    "update": {
        "required": ["id"],
        "optional": ["title", "description", "status", "appetite",
                      "assumptions", "tags", "key_results",
                      "scopes", "derived_guidelines"],
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
        },
        "invariant_texts": [
            "id: existing objective ID (O-001, etc.)",
            "Only provided fields are updated — omitted fields stay unchanged",
            "status: ACTIVE (working on it), ACHIEVED (all KRs met), ABANDONED (no longer relevant), PAUSED (on hold)",
            "key_results: update specific KRs by including their id (KR-1, etc.) with new values. "
            "Only update 'current' for progress tracking. Include {id, current} at minimum.",
            "assumptions: replaces the full list (not append-merged)",
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

VALID_STATUSES = {"ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"}


# -- Commands --

def cmd_add(args):
    """Add objectives with key results."""
    try:
        new_objectives = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_objectives, list):
        print("ERROR: --data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["add"], new_objectives)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    data = load_or_create(args.project)
    timestamp = now_iso()

    # Find next O-NNN ID
    existing_ids = [
        int(o["id"].split("-")[1]) for o in data.get("objectives", [])
        if o.get("id", "").startswith("O-")
    ]
    next_id = max(existing_ids, default=0) + 1

    added = []
    for item in new_objectives:
        obj_id = f"O-{next_id:03d}"

        # Build key results with IDs
        key_results = []
        for kr_idx, kr in enumerate(item["key_results"], 1):
            key_results.append({
                "id": f"KR-{kr_idx}",
                "metric": kr["metric"],
                "baseline": kr.get("baseline", 0),
                "target": kr["target"],
                "current": kr.get("current", kr.get("baseline", 0)),
            })

        obj = {
            "id": obj_id,
            "title": item["title"],
            "description": item["description"],
            "key_results": key_results,
            "appetite": item.get("appetite", "medium"),
            "scope": item.get("scope", "project"),
            "assumptions": item.get("assumptions", []),
            "tags": item.get("tags", []),
            "scopes": item.get("scopes", []),
            "derived_guidelines": item.get("derived_guidelines", []),
            "status": "ACTIVE",
            "created": timestamp,
            "updated": timestamp,
        }

        data["objectives"].append(obj)
        added.append(obj_id)
        next_id += 1

    save_json(args.project, data)

    print(f"Objectives saved: {args.project}")
    print(f"  Added: {len(added)} ({', '.join(added)})")
    for obj_id in added:
        obj = next(o for o in data["objectives"] if o["id"] == obj_id)
        print(f"  {obj_id}: {obj['title']}")
        for kr in obj["key_results"]:
            direction = "↑" if kr["target"] > kr["baseline"] else "↓"
            print(f"    {kr['id']}: {kr['metric']} — {kr['baseline']} {direction} {kr['target']}")


def cmd_read(args):
    """Read objectives (optionally filtered)."""
    path = objectives_path(args.project)
    if not path.exists():
        print(f"No objectives for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    objectives = data.get("objectives", [])

    if args.status:
        objectives = [o for o in objectives if o.get("status") == args.status]

    print(f"## Objectives: {args.project}")
    if args.status:
        print(f"Filter: status={args.status}")
    print(f"Count: {len(objectives)}")
    print()

    if not objectives:
        print("(none)")
        return

    print("| ID | Status | Appetite | Title | KR Progress |")
    print("|----|--------|----------|-------|-------------|")
    for o in objectives:
        kr_summary = _kr_progress_summary(o.get("key_results", []))
        title = o.get("title", "")[:35]
        print(f"| {o['id']} | {o.get('status', '')} | {o.get('appetite', '')} | {title} | {kr_summary} |")


def cmd_show(args):
    """Show full details for a single objective with coverage analysis."""
    data = load_or_create(args.project)
    obj = find_objective(data, args.objective_id)

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
    print()
    print("### Description")
    print(obj.get("description", ""))
    print()

    # Key Results with progress bars
    print("### Key Results")
    print()
    for kr in obj.get("key_results", []):
        baseline = kr.get("baseline", 0)
        target = kr["target"]
        current = kr.get("current", baseline)
        pct = _kr_percentage(baseline, target, current)
        bar = _progress_bar(pct)
        direction = "↓" if target < baseline else "↑"
        print(f"**{kr['id']}**: {kr['metric']}")
        print(f"  {baseline} {direction} **{current}** → {target}  {bar} {pct}%")
        print()

    # Assumptions
    if obj.get("assumptions"):
        print("### Assumptions")
        for a in obj["assumptions"]:
            print(f"- {a}")
        print()

    # Coverage: find linked ideas
    ideas_file = Path("forge_output") / args.project / "ideas.json"
    linked_ideas = []
    if ideas_file.exists():
        ideas_data = json.loads(ideas_file.read_text(encoding="utf-8"))
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
    tracker_file = Path("forge_output") / args.project / "tracker.json"
    if tracker_file.exists() and linked_ideas:
        tracker = json.loads(tracker_file.read_text(encoding="utf-8"))
        tasks = tracker.get("tasks", [])
        idea_ids = {i["id"] for i in linked_ideas}
        related_tasks = [t for t in tasks if t.get("origin") in idea_ids]
        if related_tasks:
            done = sum(1 for t in related_tasks if t.get("status") == "DONE")
            total = len(related_tasks)
            print(f"- **Execution progress**: {done}/{total} tasks DONE ({_pct(done, total)}%)")

    print()

    # Overall KR progress
    kr_pcts = [_kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
               for kr in obj.get("key_results", [])]
    avg_pct = sum(kr_pcts) // len(kr_pcts) if kr_pcts else 0
    print(f"- **Outcome progress**: {avg_pct}% average across KRs")


def cmd_update(args):
    """Update objective fields and KR progress."""
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
    timestamp = now_iso()

    updated = []
    for u in updates:
        obj = None
        for o in data.get("objectives", []):
            if o["id"] == u["id"]:
                obj = o
                break
        if obj is None:
            print(f"  WARNING: Objective {u['id']} not found, skipping", file=sys.stderr)
            continue

        # Simple field updates
        for field in ["title", "description", "appetite", "assumptions", "tags",
                       "scopes", "derived_guidelines"]:
            if field in u:
                obj[field] = u[field]

        # Status update with lifecycle warning (F-004)
        if "status" in u:
            new_status = u["status"]
            if new_status in VALID_STATUSES:
                old_status = obj["status"]
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
            else:
                print(f"  WARNING: Invalid status '{new_status}' for {u['id']}", file=sys.stderr)
                continue

        # Key result updates (merge by KR id)
        if "key_results" in u:
            existing_krs = {kr["id"]: kr for kr in obj.get("key_results", [])}
            for kr_update in u["key_results"]:
                kr_id = kr_update.get("id")
                if kr_id and kr_id in existing_krs:
                    for field in ["current", "metric", "baseline", "target"]:
                        if field in kr_update:
                            existing_krs[kr_id][field] = kr_update[field]
                else:
                    print(f"  WARNING: KR '{kr_id}' not found in {u['id']}, skipping",
                          file=sys.stderr)

        obj["updated"] = timestamp
        updated.append(u["id"])

    save_json(args.project, data)

    print(f"Updated {len(updated)} objectives: {args.project}")
    for obj_id in updated:
        obj = next(o for o in data["objectives"] if o["id"] == obj_id)
        print(f"  {obj_id}: {obj['title']} ({obj['status']})")
        for kr in obj.get("key_results", []):
            pct = _kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
            print(f"    {kr['id']}: {kr['metric']} — {kr.get('current', '?')}/{kr['target']} ({pct}%)")


def cmd_status(args):
    """Coverage dashboard across all objectives."""
    path = objectives_path(args.project)
    if not path.exists():
        print(f"No objectives for '{args.project}' yet.")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    objectives = data.get("objectives", [])

    if not objectives:
        print("No objectives defined.")
        return

    # Load ideas for coverage
    ideas_file = Path("forge_output") / args.project / "ideas.json"
    all_ideas = []
    if ideas_file.exists():
        ideas_data = json.loads(ideas_file.read_text(encoding="utf-8"))
        all_ideas = ideas_data.get("ideas", [])

    # Load tasks for execution progress
    tracker_file = Path("forge_output") / args.project / "tracker.json"
    all_tasks = []
    if tracker_file.exists():
        tracker = json.loads(tracker_file.read_text(encoding="utf-8"))
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
            pct = _kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
            bar = _progress_bar(pct)
            full_id = f"{obj['id']}/{kr['id']}"
            covered = "+" if full_id in covered_krs else "-"
            print(f"  [{covered}] {kr['id']}: {kr['metric']} {bar} {pct}%  ({kr.get('current', '?')}/{kr['target']})")

        # Task progress
        related_tasks = [t for t in all_tasks if t.get("origin") in idea_ids_for_obj]
        if related_tasks:
            done = sum(1 for t in related_tasks if t.get("status") == "DONE")
            total = len(related_tasks)
            print(f"  Tasks: {done}/{total} done ({_pct(done, total)}%)")

        # Summary line
        total_krs = len(kr_ids)
        covered_count = len(covered_krs)
        kr_pcts = [_kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
                   for kr in obj.get("key_results", [])]
        avg_pct = sum(kr_pcts) // len(kr_pcts) if kr_pcts else 0
        print(f"  Planning: {covered_count}/{total_krs} KRs covered | Outcome: {avg_pct}% avg")
        print()


def cmd_derive_guideline(args):
    """Create a guideline derived from an objective and link it back."""
    data = load_or_create(args.project)
    obj = None
    for o in data.get("objectives", []):
        if o["id"] == args.objective_id:
            obj = o
            break
    if not obj:
        print(f"ERROR: Objective {args.objective_id} not found", file=sys.stderr)
        sys.exit(1)

    # Parse guideline data
    try:
        guideline_data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(guideline_data, dict):
        print("ERROR: --data must be a JSON object with title, scope, content", file=sys.stderr)
        sys.exit(1)

    for field in ("title", "scope", "content"):
        if field not in guideline_data:
            print(f"ERROR: Missing required field '{field}'", file=sys.stderr)
            sys.exit(1)

    # Add derived_from to guideline
    guideline_data["derived_from"] = args.objective_id
    # Default weight to should
    guideline_data.setdefault("weight", "should")

    # Use subprocess to call guidelines add (to avoid import coupling)
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "core.guidelines", "add", args.project,
         "--data", json.dumps([guideline_data])],
        capture_output=True, text=True, encoding="utf-8"
    )

    if result.returncode != 0:
        print(f"ERROR creating guideline: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Extract guideline ID from output
    guideline_id = None
    for line in result.stdout.splitlines():
        if "G-" in line:
            import re
            match = re.search(r"(G-\d+)", line)
            if match:
                guideline_id = match.group(1)
                break

    # Link guideline back to objective
    if guideline_id:
        derived = obj.get("derived_guidelines", [])
        if guideline_id not in derived:
            derived.append(guideline_id)
            obj["derived_guidelines"] = derived
            save_json(args.project, data)

    print(result.stdout, end="")
    if guideline_id:
        print(f"  Linked: {guideline_id} → {args.objective_id} (derived_from)")
        print(f"  Objective {args.objective_id} derived_guidelines: {obj['derived_guidelines']}")


def cmd_contract(args):
    """Print contract spec for a command."""
    if args.name not in CONTRACTS:
        print(f"ERROR: Unknown contract '{args.name}'", file=sys.stderr)
        print(f"Available: {', '.join(sorted(CONTRACTS.keys()))}", file=sys.stderr)
        sys.exit(1)
    print(render_contract(args.name, CONTRACTS[args.name]))


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
        return "—"
    pcts = []
    for kr in key_results:
        pct = _kr_percentage(kr.get("baseline", 0), kr["target"], kr.get("current", kr.get("baseline", 0)))
        pcts.append(pct)
    avg = sum(pcts) // len(pcts) if pcts else 0
    return f"{avg}% ({len(pcts)} KRs)"


def _progress_bar(pct: int, width: int = 10) -> str:
    """Simple text progress bar."""
    filled = int(width * pct / 100)
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}]"


def _pct(done: int, total: int) -> int:
    return int(done / total * 100) if total > 0 else 0


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Objectives — business goals with measurable key results")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Add objectives")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("read", help="Read objectives")
    p.add_argument("project")
    p.add_argument("--status", help="Filter by status")

    p = sub.add_parser("show", help="Show objective details + coverage")
    p.add_argument("project")
    p.add_argument("objective_id")

    p = sub.add_parser("update", help="Update objectives / KR progress")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("status", help="Coverage dashboard")
    p.add_argument("project")

    p = sub.add_parser("derive-guideline", help="Create a guideline derived from an objective")
    p.add_argument("project")
    p.add_argument("objective_id", help="Objective ID (e.g. O-001)")
    p.add_argument("--data", required=True, help='JSON: {"title":"...","scope":"...","content":"..."}')

    p = sub.add_parser("contract", help="Print contract spec")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "read": cmd_read,
        "show": cmd_show,
        "update": cmd_update,
        "status": cmd_status,
        "derive-guideline": cmd_derive_guideline,
        "contract": cmd_contract,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
