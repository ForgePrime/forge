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
    add               {project} --data '{json}'     Add lessons learned
    read              {project}                      Read lessons for project
    read-all                                         Read lessons across all projects
    promote           {lesson_id} [--scope X] [--weight X]  Promote lesson to global guideline
    promote-knowledge {lesson_id} [--category X] [--scopes X]  Promote lesson to knowledge object
    contract                                         Print contract spec
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from entity_base import EntityModule, make_cli
from errors import EntityNotFound, PreconditionError
from models import Lesson
from storage import JSONFileStorage, now_iso
from trace import trace_cmd


# -- Contract --

CONTRACTS = {
    "add": {
        "required": ["category", "title", "detail"],
        "optional": ["task_id", "decision_ids", "severity", "applies_to", "tags",
                      "promoted_to_guideline", "promoted_to_knowledge"],
        "enums": {
            "category": {
                "pattern-discovered",
                "mistake-avoided",
                "decision-validated",
                "decision-reversed",
                "tool-insight",
                "architecture-lesson",
                "process-improvement",
                "market-insight",
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
            "promoted_to_guideline: G-NNN ID if this lesson was promoted to a guideline (auto-set by promote command)",
            "promoted_to_knowledge: K-NNN ID if this lesson was promoted to knowledge (auto-set by promote-knowledge command)",
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


# -- Module --

class Lessons(EntityModule):
    entity_type = "lessons"
    list_key = "lessons"
    id_prefix = "L"
    contracts = CONTRACTS
    display_name = "Lessons"
    model_class = Lesson

    def build_entity(self, input_item, entity_id, timestamp, args):
        return {
            "id": entity_id,
            "category": input_item["category"],
            "title": input_item["title"],
            "detail": input_item["detail"],
            "task_id": input_item.get("task_id", ""),
            "decision_ids": input_item.get("decision_ids", []),
            "severity": input_item.get("severity", "important"),
            "applies_to": input_item.get("applies_to", ""),
            "tags": input_item.get("tags", []),
            "project": args.project,
            "timestamp": timestamp,
        }

    def print_add_summary(self, project, data, added, skipped):
        print(f"Lessons recorded: {project}")
        print(f"  Added: {len(added)} ({', '.join(added)})")
        print(f"  Total: {len(self.items(data))}")

    def render_list(self, items, args):
        print(f"## Lessons: {args.project}")
        print(f"Count: {len(items)}")
        print()
        if not items:
            print("(none)")
            return
        for l in items:
            severity_icon = {"critical": "!!!", "important": " ! ", "minor": "   "}.get(
                l.get("severity", ""), "   ")
            print(f"### {l['id']} [{severity_icon}] {l['title']}")
            print(f"Category: {l['category']} | Applies to: {l.get('applies_to', '(general)')}")
            print(f"{l['detail']}")
            if l.get("tags"):
                print(f"Tags: {', '.join(l['tags'])}")
            print()


_mod = Lessons()

# Public API used by other modules
load_or_create = _mod.load
save_json = _mod.save


# -- Custom commands --

def cmd_read_all(args):
    """Read lessons across all projects (with optional filtering)."""
    storage = JSONFileStorage()
    projects = storage.list_projects()
    if not projects:
        print("No projects found.")
        return

    all_lessons = []
    for project in projects:
        if storage.exists(project, 'lessons'):
            data = storage.load_data(project, 'lessons')
            all_lessons.extend(data.get("lessons", []))

    if not all_lessons:
        print("No lessons recorded across any project.")
        return

    if args.severity:
        all_lessons = [l for l in all_lessons if l.get("severity") == args.severity]
    if args.category:
        all_lessons = [l for l in all_lessons if l.get("category") == args.category]
    if args.tags:
        filter_tags = {t.strip().lower() for t in args.tags.split(",")}
        all_lessons = [l for l in all_lessons
                       if filter_tags & {t.lower() for t in l.get("tags", [])}]

    severity_order = {"critical": 0, "important": 1, "minor": 2}
    all_lessons.sort(key=lambda l: (severity_order.get(l.get("severity", "minor"), 2), l.get("timestamp", "")))

    limit = args.limit or 0
    total_before_limit = len(all_lessons)
    if limit > 0:
        all_lessons = all_lessons[:limit]

    filters = []
    if args.severity:
        filters.append(f"severity={args.severity}")
    if args.category:
        filters.append(f"category={args.category}")
    if args.tags:
        filters.append(f"tags={args.tags}")
    if limit > 0:
        filters.append(f"limit={limit}")

    print(f"## All Lessons ({len(all_lessons)}{f'/{total_before_limit}' if limit and total_before_limit > limit else ''} total)")
    if filters:
        print(f"Filter: {', '.join(filters)}")
    print()

    for l in all_lessons:
        severity_icon = {"critical": "!!!", "important": " ! ", "minor": "   "}.get(l.get("severity", ""), "   ")
        print(f"### {l['id']} [{severity_icon}] {l['title']} (from: {l.get('project', '?')})")
        print(f"Category: {l['category']} | Applies to: {l.get('applies_to', '(general)')}")
        print(f"{l['detail']}")
        if l.get("tags"):
            print(f"Tags: {', '.join(l['tags'])}")
        print()


def cmd_promote(args):
    """Promote a lesson to a global guideline."""
    storage = JSONFileStorage()
    projects = storage.list_projects()
    if not projects:
        raise PreconditionError("No projects found.")

    found = None
    for project in projects:
        if storage.exists(project, 'lessons'):
            data = storage.load_data(project, 'lessons')
            for l in data.get("lessons", []):
                if l.get("id") == args.lesson_id:
                    found = l
                    break
        if found:
            break

    if not found:
        raise EntityNotFound(f"Lesson {args.lesson_id} not found")

    if found.get("promoted_to_guideline"):
        print(f"WARNING: Lesson {args.lesson_id} already promoted to {found['promoted_to_guideline']}")
        print("Skipping.")
        return

    global_data = storage.load_global('guidelines')

    for g in global_data.get("guidelines", []):
        if g.get("title", "").lower() == found["title"].lower():
            print(f"WARNING: Guideline with similar title already exists: {g['id']}")
            print(f"  Title: {g['title']}")
            print("Skipping promotion.")
            return

    existing_ids = [
        int(g["id"].split("-")[1]) for g in global_data.get("guidelines", [])
        if g.get("id", "").startswith("G-")
    ]
    next_id = max(existing_ids, default=0) + 1

    weight_map = {"critical": "must", "important": "should", "minor": "may"}
    weight = weight_map.get(found.get("severity", "important"), "should")
    if args.weight:
        weight = args.weight

    scope = args.scope or "general"

    guideline = {
        "id": f"G-{next_id:03d}",
        "title": found["title"],
        "scope": scope,
        "content": found["detail"],
        "rationale": f"Promoted from lesson {found['id']} (project: {found.get('project', '?')}). Category: {found['category']}. Applies to: {found.get('applies_to', 'general')}.",
        "weight": weight,
        "tags": found.get("tags", []),
        "status": "ACTIVE",
        "promoted_from": found["id"],
        "timestamp": now_iso(),
    }

    global_data["guidelines"].append(guideline)
    storage.save_global('guidelines', global_data)

    lesson_project = found.get("project", project)
    lesson_data = storage.load_data(lesson_project, 'lessons')
    for l in lesson_data.get("lessons", []):
        if l["id"] == found["id"]:
            l["promoted_to_guideline"] = guideline["id"]
            break
    storage.save_data(lesson_project, 'lessons', lesson_data)
    trace_cmd(lesson_project, "lessons", "promote",
              lesson_id=found["id"], guideline_id=guideline["id"])

    print(f"Lesson promoted to global guideline:")
    print(f"  {found['id']} → {guideline['id']}")
    print(f"  Title: {guideline['title']}")
    print(f"  Scope: {scope} | Weight: {weight}")
    print(f"  Source: {found.get('project', '?')}/{found['id']}")


def cmd_promote_knowledge(args):
    """Promote a lesson to a knowledge object."""
    storage = JSONFileStorage()
    projects = storage.list_projects()
    if not projects:
        raise PreconditionError("No projects found.")

    found = None
    lesson_project = None
    for project in projects:
        if storage.exists(project, 'lessons'):
            data = storage.load_data(project, 'lessons')
            for l in data.get("lessons", []):
                if l.get("id") == args.lesson_id:
                    found = l
                    lesson_project = project
                    break
        if found:
            break

    if not found:
        raise EntityNotFound(f"Lesson {args.lesson_id} not found")

    if found.get("promoted_to_knowledge"):
        print(f"WARNING: Lesson {args.lesson_id} already promoted to {found['promoted_to_knowledge']}")
        print("Skipping.")
        return

    target_project = lesson_project

    category_map = {
        "pattern-discovered": "code-patterns",
        "mistake-avoided": "technical-context",
        "decision-validated": "architecture",
        "decision-reversed": "architecture",
        "tool-insight": "technical-context",
        "architecture-lesson": "architecture",
        "process-improvement": "technical-context",
        "market-insight": "business-context",
    }
    category = args.category or category_map.get(found.get("category", ""), "technical-context")

    k_data = storage.load_data(target_project, 'knowledge')
    existing_keys = {
        (k.get("category", "").lower().strip(), k.get("title", "").lower().strip())
        for k in k_data.get("knowledge", [])
    }
    if (category.lower().strip(), found["title"].lower().strip()) in existing_keys:
        print(f"WARNING: Knowledge with same category+title already exists. Skipping.")
        return

    existing_ids = [
        int(k["id"].split("-")[1]) for k in k_data.get("knowledge", [])
        if k.get("id", "").startswith("K-")
    ]
    k_num = max(existing_ids, default=0) + 1
    k_id = f"K-{k_num:03d}"

    timestamp = now_iso()
    scopes = []
    if args.scopes:
        scopes = [s.strip() for s in args.scopes.split(",")]
    elif found.get("tags"):
        scopes = found["tags"][:3]

    knowledge = {
        "id": k_id,
        "title": found["title"],
        "category": category,
        "content": found["detail"],
        "status": "DRAFT",
        "version": 1,
        "scopes": scopes,
        "tags": found.get("tags", []),
        "source": {
            "type": "lesson",
            "ref": found["id"],
            "derived_from_lessons": [found["id"]],
        },
        "linked_entities": [
            {
                "entity_type": "lesson",
                "entity_id": found["id"],
                "relation": "reference",
            },
        ],
        "dependencies": [],
        "versions": [
            {
                "version": 1,
                "content": found["detail"],
                "changed_by": "forge",
                "changed_at": timestamp,
                "change_reason": f"Promoted from lesson {found['id']}",
            },
        ],
        "review": {
            "last_reviewed_at": timestamp,
            "review_interval_days": 30,
            "next_review_at": None,
        },
        "created_at": timestamp,
        "updated_at": timestamp,
        "created_by": "forge",
    }

    k_data["knowledge"].append(knowledge)
    storage.save_data(target_project, 'knowledge', k_data)

    lesson_data = storage.load_data(lesson_project, 'lessons')
    for l in lesson_data.get("lessons", []):
        if l["id"] == found["id"]:
            l["promoted_to_knowledge"] = k_id
            break
    storage.save_data(lesson_project, 'lessons', lesson_data)
    trace_cmd(lesson_project, "lessons", "promote_knowledge",
              lesson_id=found["id"], knowledge_id=k_id)

    print(f"Lesson promoted to knowledge:")
    print(f"  {found['id']} → {k_id}")
    print(f"  Title: {knowledge['title']}")
    print(f"  Category: {category} | Status: DRAFT")
    print(f"  Scopes: {', '.join(scopes) if scopes else '(none)'}")
    print(f"  Source: {lesson_project}/{found['id']}")
    print(f"\nReview and activate: python -m core.knowledge update {target_project} "
          f"--data '{{\"id\": \"{k_id}\", \"status\": \"ACTIVE\"}}'")


# -- CLI --

def _setup_extra_parsers(sub):
    p = sub.add_parser("read-all", help="Read lessons across all projects")
    p.add_argument("--severity", help="Filter by severity (critical, important, minor)")
    p.add_argument("--category", help="Filter by category")
    p.add_argument("--tags", help="Filter by tags (comma-separated, OR match)")
    p.add_argument("--limit", type=int, help="Max number of lessons to return")

    p = sub.add_parser("promote", help="Promote a lesson to a global guideline")
    p.add_argument("lesson_id", help="Lesson ID (e.g. L-001)")
    p.add_argument("--scope", help="Guideline scope (default: general)")
    p.add_argument("--weight", choices=["must", "should", "may"],
                   help="Override weight (default: based on severity)")

    p = sub.add_parser("promote-knowledge", help="Promote a lesson to a knowledge object")
    p.add_argument("lesson_id", help="Lesson ID (e.g. L-001)")
    p.add_argument("--category", help="Knowledge category (default: inferred from lesson category)")
    p.add_argument("--scopes", help="Comma-separated scopes (default: from lesson tags)")


def main():
    make_cli(
        _mod,
        extra_commands={
            "read-all": cmd_read_all,
            "promote": cmd_promote,
            "promote-knowledge": cmd_promote_knowledge,
        },
        setup_extra_parsers=_setup_extra_parsers,
        description="Forge Lessons -- compound learning from project execution",
    )


if __name__ == "__main__":
    main()
