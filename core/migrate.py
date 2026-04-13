"""
Forge Migrate — Import JSON project data into PostgreSQL.

Reads all entity JSON files from a project directory, inserts them into
PostgreSQL tables with proper FK resolution, junction table population,
and knowledge version import.

Usage:
    python -m core.migrate import {project_dir} [--database-url URL]
    python -m core.migrate import {project_dir} --dry-run
    python -m core.migrate status {project_dir}

Reference: docs/FORGE-PLATFORM-V2.md Section 7.3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    from psycopg2 import sql as pgsql
except ImportError:
    psycopg2 = None  # type: ignore
    pgsql = None  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _compat import configure_encoding
configure_encoding()


# -----------------------------------------------------------------------
# Entity file → (JSON list key, DB table name, ext_id prefix)
# -----------------------------------------------------------------------
ENTITY_FILES = {
    "tracker.json": ("tasks", "tasks", "T"),
    "decisions.json": ("decisions", "decisions", "D"),
    "changes.json": ("changes", "changes", "C"),
    "guidelines.json": ("guidelines", "guidelines", "G"),
    "ideas.json": ("ideas", "ideas", "I"),
    "objectives.json": ("objectives", "objectives", "O"),
    "lessons.json": ("lessons", "lessons", "L"),
    "knowledge.json": ("knowledge", "knowledge", "K"),
    "ac_templates.json": ("ac_templates", "ac_templates", "AC"),
}

# Allowed table names (prevents SQL injection via table interpolation)
ALLOWED_TABLES = set(info[1] for info in ENTITY_FILES.values())

# Columns that are JSONB in PostgreSQL
JSONB_COLUMNS = {
    "config", "assumptions", "acceptance_criteria", "test_requirements",
    "alternatives", "findings", "options", "open_questions", "blockers",
    "evidence_refs", "reasoning_trace", "examples", "parameters",
    "linked_entities", "review",
}

# Columns that are TEXT[] arrays in PostgreSQL
ARRAY_COLUMNS = {
    "tags", "scopes", "knowledge_ids", "derived_guidelines",
    "advances_key_results", "guidelines", "depends_on", "conflicts_with",
    "blocked_by_decisions", "decision_ids", "guidelines_checked",
    "dependencies",
}

# BOOLEAN columns — need explicit coercion from JSON string/truthy
BOOLEAN_COLUMNS = {"parallel", "ready_for_tracker", "required"}

# INT columns — need explicit coercion
INT_COLUMNS = {"lines_added", "lines_removed", "usage_count", "current_version"}

# JSON timestamp key → DB column mapping (per entity table)
TS_MAP = {
    "changes": {"timestamp": "recorded_at"},
    "decisions": {"timestamp": "created_at"},
    "lessons": {"timestamp": "created_at"},
}

# Known columns per table (matching storage_pg.py)
TABLE_COLUMNS = {
    "tasks": {
        "ext_id", "name", "description", "instruction", "type", "status",
        "origin", "skill", "parallel",
        "acceptance_criteria", "test_requirements", "depends_on",
        "conflicts_with", "knowledge_ids", "scopes", "blocked_by_decisions",
        "agent", "failed_reason", "started_at", "completed_at",
        "created_at", "updated_at",
        # Note: origin_idea_id excluded — resolved as FK in second pass
    },
    "decisions": {
        "ext_id", "task_id", "type", "status", "issue", "recommendation",
        "reasoning", "alternatives", "confidence", "decided_by", "file",
        "scope", "tags", "exploration_type", "findings", "options",
        "open_questions", "severity", "likelihood", "linked_entity_type",
        "linked_entity_id", "mitigation_plan", "resolution_notes",
        "blockers", "ready_for_tracker", "evidence_refs",
        "created_at", "updated_at",
    },
    "changes": {
        "ext_id", "task_id", "file", "action", "summary", "reasoning_trace",
        "decision_ids", "guidelines_checked", "group_id",
        "lines_added", "lines_removed", "recorded_at",
    },
    "guidelines": {
        "ext_id", "title", "scope", "content", "rationale", "examples",
        "tags", "weight", "status", "derived_from", "imported_from",
        "promoted_from", "created_at", "updated_at",
    },
    "ideas": {
        "ext_id", "title", "description", "category", "status",
        "appetite", "priority", "tags", "scopes", "knowledge_ids",
        "guidelines", "advances_key_results", "rejection_reason",
        "merged_into", "exploration_notes", "committed_at",
        "created_at", "updated_at",
        # Note: parent_id excluded — resolved as FK in second pass
    },
    "objectives": {
        "ext_id", "title", "description", "appetite", "scope", "status",
        "assumptions", "tags", "scopes", "derived_guidelines",
        "knowledge_ids", "created_at", "updated_at",
    },
    "lessons": {
        "ext_id", "category", "title", "detail", "task_id", "decision_ids",
        "severity", "applies_to", "tags", "promoted_to_guideline",
        "promoted_to_knowledge", "created_at",
    },
    "knowledge": {
        "ext_id", "title", "category", "content", "current_version",
        "status", "scopes", "tags", "dependencies", "source",
        "source_type", "created_by", "linked_entities", "review",
        "created_at", "updated_at",
    },
    "ac_templates": {
        "ext_id", "title", "description", "template", "category",
        "verification_method", "parameters", "scopes", "tags",
        "status", "usage_count", "created_at", "updated_at",
    },
}


# -----------------------------------------------------------------------
# JSON → DB row conversion
# -----------------------------------------------------------------------

def item_to_row(item: dict, table: str, project_id: int) -> dict:
    """Convert a JSON entity dict to a DB-insertable row dict.

    Handles timestamp mapping, JSONB serialization, type coercion
    for BOOLEAN/INT columns, and known-column filtering.
    """
    ts_overrides = TS_MAP.get(table, {})
    known_cols = TABLE_COLUMNS.get(table)

    row = {"project_id": project_id}

    for key, value in item.items():
        # Skip internal/handled-separately fields
        if key in ("_db_id", "project", "versions", "version", "source",
                    "parent_id", "origin_idea_id", "key_results",
                    "related_ideas", "relations"):
            continue
        # id → ext_id
        if key == "id":
            row["ext_id"] = value
            continue
        # Timestamp overrides
        if key in ts_overrides:
            row[ts_overrides[key]] = value
            continue
        if key in ("created", "updated"):
            row[key + "_at"] = value
            continue
        # BOOLEAN coercion
        if key in BOOLEAN_COLUMNS:
            if isinstance(value, str):
                row[key] = value.lower() in ("true", "1", "yes")
            else:
                row[key] = bool(value) if value is not None else False
            continue
        # INT coercion
        if key in INT_COLUMNS:
            try:
                row[key] = int(value) if value is not None else 0
            except (ValueError, TypeError):
                row[key] = 0
            continue
        # JSONB columns → serialize
        if key in JSONB_COLUMNS and value is not None:
            row[key] = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            continue
        row[key] = value

    # Handle 'source' field for knowledge → decompose to source (TEXT) + source_type
    if table == "knowledge" and "source" in item:
        src = item["source"]
        if isinstance(src, dict):
            row["source_type"] = src.get("type", "")
            row["source"] = src.get("ref", "")
            if src.get("derived_from_lessons"):
                print(f"  NOTE: {item.get('id', '?')}.source.derived_from_lessons "
                      f"({len(src['derived_from_lessons'])} items) — not stored in DB",
                      file=sys.stderr)
        elif isinstance(src, str):
            row["source"] = src

    # Handle 'version' → current_version for knowledge
    if table == "knowledge" and "version" in item:
        row["current_version"] = int(item["version"])

    # Filter to known columns
    if known_cols is not None:
        allowed = known_cols | {"project_id", "ext_id"}
        row = {k: v for k, v in row.items() if k in allowed}

    return row


def insert_row(cur, table: str, row: dict) -> int:
    """INSERT a row using safe SQL identifiers and return the new id."""
    assert table in ALLOWED_TABLES, f"Unknown table: {table}"
    cols = list(row.keys())
    query = pgsql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
        pgsql.Identifier(table),
        pgsql.SQL(", ").join(map(pgsql.Identifier, cols)),
        pgsql.SQL(", ").join(pgsql.Placeholder() * len(cols)),
    )
    cur.execute(query, [row[c] for c in cols])
    return cur.fetchone()["id"]


# -----------------------------------------------------------------------
# FK resolution (second pass)
# -----------------------------------------------------------------------

def resolve_idea_parent_ids(cur, ideas_data: list, id_map: dict):
    """Resolve ideas.parent_id from ext_id to DB id (second pass)."""
    count = 0
    for idea in ideas_data:
        parent_ext = idea.get("parent_id")
        if not parent_ext:
            continue
        idea_db_id = id_map.get(("ideas", idea.get("id", "")))
        parent_db_id = id_map.get(("ideas", parent_ext))
        if idea_db_id and parent_db_id:
            cur.execute(
                "UPDATE ideas SET parent_id = %s WHERE id = %s",
                (parent_db_id, idea_db_id),
            )
            count += 1
        elif idea_db_id:
            print(f"  WARNING: idea {idea['id']}.parent_id={parent_ext} not found",
                  file=sys.stderr)
    return count


def resolve_task_origin_idea_ids(cur, tasks_data: list, id_map: dict):
    """Resolve tasks.origin_idea_id from origin field to DB id."""
    count = 0
    for task in tasks_data:
        origin = task.get("origin", "")
        if not origin.startswith("I-"):
            continue
        task_db_id = id_map.get(("tasks", task.get("id", "")))
        idea_db_id = id_map.get(("ideas", origin))
        if task_db_id and idea_db_id:
            cur.execute(
                "UPDATE tasks SET origin_idea_id = %s WHERE id = %s",
                (idea_db_id, task_db_id),
            )
            count += 1
    return count


# -----------------------------------------------------------------------
# Junction table importers
# -----------------------------------------------------------------------

def import_task_dependencies(cur, tasks_data: list, id_map: dict):
    """Create task_dependencies rows from depends_on arrays."""
    count = 0
    for task in tasks_data:
        task_db_id = id_map.get(("tasks", task.get("id", "")))
        if not task_db_id:
            continue
        for dep_ext_id in task.get("depends_on", []):
            dep_db_id = id_map.get(("tasks", dep_ext_id))
            if dep_db_id:
                cur.execute(
                    "INSERT INTO task_dependencies (task_id, depends_on_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (task_db_id, dep_db_id),
                )
                count += 1
    return count


def import_task_conflicts(cur, tasks_data: list, id_map: dict):
    """Create task_conflicts rows from conflicts_with arrays."""
    count = 0
    for task in tasks_data:
        task_db_id = id_map.get(("tasks", task.get("id", "")))
        if not task_db_id:
            continue
        for conflict_ext_id in task.get("conflicts_with", []):
            conflict_db_id = id_map.get(("tasks", conflict_ext_id))
            if conflict_db_id:
                cur.execute(
                    "INSERT INTO task_conflicts (task_id, conflicts_with_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (task_db_id, conflict_db_id),
                )
                count += 1
    return count


def import_task_knowledge(cur, tasks_data: list, id_map: dict):
    """Create task_knowledge rows from knowledge_ids arrays."""
    count = 0
    for task in tasks_data:
        task_db_id = id_map.get(("tasks", task.get("id", "")))
        if not task_db_id:
            continue
        for k_ext_id in task.get("knowledge_ids", []):
            k_db_id = id_map.get(("knowledge", k_ext_id))
            if k_db_id:
                cur.execute(
                    "INSERT INTO task_knowledge (task_id, knowledge_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (task_db_id, k_db_id),
                )
                count += 1
    return count


def import_knowledge_links(cur, knowledge_data: list, id_map: dict):
    """Create knowledge_links rows from linked_entities arrays."""
    count = 0
    for k in knowledge_data:
        k_db_id = id_map.get(("knowledge", k.get("id", "")))
        if not k_db_id:
            continue
        for le in k.get("linked_entities", []):
            entity_type = le.get("entity_type", "")
            entity_ext_id = le.get("entity_id", "")
            relation = le.get("relation", "reference")
            table = _entity_type_to_table(entity_type)
            entity_db_id = id_map.get((table, entity_ext_id))
            if entity_db_id:
                cur.execute(
                    "INSERT INTO knowledge_links "
                    "(knowledge_id, entity_type, entity_id, relation) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (k_db_id, entity_type, entity_db_id, relation),
                )
                count += 1
    return count


def import_knowledge_versions(cur, knowledge_data: list, id_map: dict):
    """Import embedded version arrays into knowledge_versions table."""
    count = 0
    for k in knowledge_data:
        k_db_id = id_map.get(("knowledge", k.get("id", "")))
        if not k_db_id:
            continue
        for v in k.get("versions", []):
            cur.execute(
                "INSERT INTO knowledge_versions "
                "(knowledge_id, version, content, changed_by, change_reason) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (
                    k_db_id,
                    int(v.get("version", 1)),
                    v.get("content", ""),
                    v.get("changed_by", ""),
                    v.get("change_reason", ""),
                ),
            )
            count += 1
    return count


def import_key_results(cur, objectives_data: list, id_map: dict):
    """Import key_results from objectives' nested arrays."""
    count = 0
    for obj in objectives_data:
        obj_db_id = id_map.get(("objectives", obj.get("id", "")))
        if not obj_db_id:
            continue
        for kr in obj.get("key_results", []):
            cur.execute(
                "INSERT INTO key_results "
                "(objective_id, ext_id, metric, baseline, target, current) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (
                    obj_db_id,
                    kr.get("id", ""),
                    kr.get("metric", ""),
                    kr.get("baseline", 0),
                    kr.get("target", 0),
                    kr.get("current", 0),
                ),
            )
            count += 1
    return count


def import_change_decisions(cur, changes_data: list, id_map: dict):
    """Create change_decisions rows from decision_ids arrays."""
    count = 0
    for change in changes_data:
        change_db_id = id_map.get(("changes", change.get("id", "")))
        if not change_db_id:
            continue
        for d_ext_id in change.get("decision_ids", []):
            d_db_id = id_map.get(("decisions", d_ext_id))
            if d_db_id:
                cur.execute(
                    "INSERT INTO change_decisions (change_id, decision_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (change_db_id, d_db_id),
                )
                count += 1
    return count


def import_change_guidelines(cur, changes_data: list, id_map: dict):
    """Create change_guidelines rows from guidelines_checked arrays."""
    count = 0
    for change in changes_data:
        change_db_id = id_map.get(("changes", change.get("id", "")))
        if not change_db_id:
            continue
        for g_ext_id in change.get("guidelines_checked", []):
            g_db_id = id_map.get(("guidelines", g_ext_id))
            if g_db_id:
                cur.execute(
                    "INSERT INTO change_guidelines (change_id, guideline_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (change_db_id, g_db_id),
                )
                count += 1
    return count


def import_lesson_decisions(cur, lessons_data: list, id_map: dict):
    """Create lesson_decisions rows from decision_ids arrays."""
    count = 0
    for lesson in lessons_data:
        lesson_db_id = id_map.get(("lessons", lesson.get("id", "")))
        if not lesson_db_id:
            continue
        for d_ext_id in lesson.get("decision_ids", []):
            d_db_id = id_map.get(("decisions", d_ext_id))
            if d_db_id:
                cur.execute(
                    "INSERT INTO lesson_decisions (lesson_id, decision_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (lesson_db_id, d_db_id),
                )
                count += 1
    return count


def import_task_decisions(cur, tasks_data: list, id_map: dict):
    """Create task_decisions rows from blocked_by_decisions arrays."""
    count = 0
    for task in tasks_data:
        task_db_id = id_map.get(("tasks", task.get("id", "")))
        if not task_db_id:
            continue
        for d_ext_id in task.get("blocked_by_decisions", []):
            d_db_id = id_map.get(("decisions", d_ext_id))
            if d_db_id:
                cur.execute(
                    "INSERT INTO task_decisions (task_id, decision_id, relation) "
                    "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (task_db_id, d_db_id, "blocked-by"),
                )
                count += 1
    return count


def import_gates(cur, project_id: int, config: dict):
    """Import gate configurations from tracker config."""
    gates = config.get("gates", [])
    count = 0
    for gate in gates:
        name = gate.get("name", "")
        command = gate.get("command", gate.get("cmd", ""))
        if not name or not command:
            continue
        cur.execute(
            "INSERT INTO gates (project_id, name, command, required) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (project_id, name, command, gate.get("required", True)),
        )
        count += 1
    return count


def _entity_type_to_table(entity_type: str) -> str:
    """Map entity_type string to DB table name."""
    mapping = {
        "task": "tasks",
        "idea": "ideas",
        "objective": "objectives",
        "decision": "decisions",
        "guideline": "guidelines",
        "knowledge": "knowledge",
        "lesson": "lessons",
    }
    return mapping.get(entity_type, entity_type)


# -----------------------------------------------------------------------
# Main import logic
# -----------------------------------------------------------------------

def load_json_file(path: Path) -> dict | None:
    """Load a JSON file, return None if not found or invalid."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Failed to read {path}: {e}", file=sys.stderr)
        return None


def cmd_import(args):
    """Import a JSON project into PostgreSQL."""
    from errors import PreconditionError, EntityNotFound

    if psycopg2 is None:
        raise PreconditionError("psycopg2 not installed.")

    source_dir = Path(args.source)
    if not source_dir.is_dir():
        raise EntityNotFound(f"Source directory not found: {source_dir}")

    database_url = args.database_url or os.environ.get(
        "DATABASE_URL", "postgresql://forge:forge@localhost:5432/forge_db"
    )

    # Detect project slug from tracker.json
    tracker_data = load_json_file(source_dir / "tracker.json")
    if tracker_data is None:
        raise EntityNotFound(f"No tracker.json found in {source_dir}")

    project_slug = tracker_data.get("project", source_dir.name)
    print(f"## Forge Migrate: {project_slug}")
    print(f"Source: {source_dir}")
    print(f"Target: {database_url[:50]}...")
    print()

    if args.dry_run:
        print("--- DRY RUN MODE ---")
        print()

    # Scan available entity files
    available = {}
    for filename, (list_key, table, prefix) in ENTITY_FILES.items():
        data = load_json_file(source_dir / filename)
        if data is not None:
            items = data.get(list_key, [])
            available[filename] = {
                "data": data,
                "items": items,
                "list_key": list_key,
                "table": table,
                "prefix": prefix,
                "count": len(items),
            }

    print("### Source data:")
    for fn, info in sorted(available.items()):
        print(f"  {fn}: {info['count']} items")
    print()

    if args.dry_run:
        total = sum(info["count"] for info in available.values())
        print(f"Total entities to import: {total}")
        print("(dry run — no changes made)")
        return

    # Connect and import
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Ensure project exists
            cur.execute("SELECT id FROM projects WHERE slug = %s", (project_slug,))
            row = cur.fetchone()
            if row:
                project_id = row["id"]
                print(f"Project '{project_slug}' already exists (id={project_id})")
            else:
                goal = tracker_data.get("goal", "")
                config = tracker_data.get("config", {})
                cur.execute(
                    "INSERT INTO projects (slug, goal, config) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (project_slug, goal, json.dumps(config, ensure_ascii=False)),
                )
                project_id = cur.fetchone()["id"]
                print(f"Created project '{project_slug}' (id={project_id})")

            # id_map: (table, ext_id) → db_id
            id_map: dict[tuple[str, str], int] = {}
            stats = {"entities": 0, "junctions": 0, "versions": 0, "warnings": 0}

            # Import order matters for FK resolution
            import_order = [
                "objectives.json",
                "ideas.json",
                "tracker.json",
                "decisions.json",
                "guidelines.json",
                "knowledge.json",
                "changes.json",
                "lessons.json",
                "ac_templates.json",
            ]

            for filename in import_order:
                if filename not in available:
                    continue
                info = available[filename]
                table = info["table"]
                items = info["items"]

                imported = 0
                skipped = 0
                for item in items:
                    ext_id = item.get("id", "")
                    if not ext_id:
                        print(f"  WARNING: Item without id in {filename}, skipping",
                              file=sys.stderr)
                        skipped += 1
                        stats["warnings"] += 1
                        continue

                    # Check if already exists
                    cur.execute(
                        pgsql.SQL("SELECT id FROM {} WHERE project_id = %s AND ext_id = %s").format(
                            pgsql.Identifier(table)
                        ),
                        (project_id, ext_id),
                    )
                    existing = cur.fetchone()
                    if existing:
                        id_map[(table, ext_id)] = existing["id"]
                        skipped += 1
                        continue

                    row = item_to_row(item, table, project_id)
                    try:
                        # Use SAVEPOINT for per-entity error recovery (F-02 fix)
                        cur.execute("SAVEPOINT sp_entity")
                        db_id = insert_row(cur, table, row)
                        cur.execute("RELEASE SAVEPOINT sp_entity")
                        id_map[(table, ext_id)] = db_id
                        imported += 1
                    except Exception as e:
                        cur.execute("ROLLBACK TO SAVEPOINT sp_entity")
                        print(f"  WARNING: Failed to insert {table}/{ext_id}: {e}",
                              file=sys.stderr)
                        stats["warnings"] += 1
                        skipped += 1
                        continue

                stats["entities"] += imported
                if imported > 0 or skipped > 0:
                    print(f"  {table}: {imported} imported, {skipped} skipped")

            # Second pass: resolve FK references (F-03, F-04 fix)
            print()
            print("### FK resolution:")

            if "ideas.json" in available:
                n = resolve_idea_parent_ids(
                    cur, available["ideas.json"]["items"], id_map
                )
                if n:
                    print(f"  ideas.parent_id: {n} resolved")

            if "tracker.json" in available:
                n = resolve_task_origin_idea_ids(
                    cur, available["tracker.json"]["items"], id_map
                )
                if n:
                    print(f"  tasks.origin_idea_id: {n} resolved")

            # Junction tables
            print()
            print("### Junction tables:")

            if "tracker.json" in available:
                tasks = available["tracker.json"]["items"]
                n = import_task_dependencies(cur, tasks, id_map)
                if n:
                    print(f"  task_dependencies: {n}")
                    stats["junctions"] += n

                n = import_task_conflicts(cur, tasks, id_map)
                if n:
                    print(f"  task_conflicts: {n}")
                    stats["junctions"] += n

                n = import_task_knowledge(cur, tasks, id_map)
                if n:
                    print(f"  task_knowledge: {n}")
                    stats["junctions"] += n

                n = import_task_decisions(cur, tasks, id_map)
                if n:
                    print(f"  task_decisions: {n}")
                    stats["junctions"] += n

            if "knowledge.json" in available:
                knowledge = available["knowledge.json"]["items"]
                n = import_knowledge_links(cur, knowledge, id_map)
                if n:
                    print(f"  knowledge_links: {n}")
                    stats["junctions"] += n

                n = import_knowledge_versions(cur, knowledge, id_map)
                if n:
                    print(f"  knowledge_versions: {n}")
                    stats["versions"] += n

            if "objectives.json" in available:
                objectives = available["objectives.json"]["items"]
                n = import_key_results(cur, objectives, id_map)
                if n:
                    print(f"  key_results: {n}")
                    stats["junctions"] += n

            if "changes.json" in available:
                changes = available["changes.json"]["items"]
                n = import_change_decisions(cur, changes, id_map)
                if n:
                    print(f"  change_decisions: {n}")
                    stats["junctions"] += n

                n = import_change_guidelines(cur, changes, id_map)
                if n:
                    print(f"  change_guidelines: {n}")
                    stats["junctions"] += n

            if "lessons.json" in available:
                lessons = available["lessons.json"]["items"]
                n = import_lesson_decisions(cur, lessons, id_map)
                if n:
                    print(f"  lesson_decisions: {n}")
                    stats["junctions"] += n

            # Gates
            config = tracker_data.get("config", {})
            if config.get("gates"):
                n = import_gates(cur, project_id, config)
                if n:
                    print(f"  gates: {n}")
                    stats["junctions"] += n

        conn.commit()

        print()
        print("### Summary:")
        print(f"  Entities imported: {stats['entities']}")
        print(f"  Junction rows: {stats['junctions']}")
        print(f"  Knowledge versions: {stats['versions']}")
        if stats["warnings"]:
            print(f"  Warnings: {stats['warnings']}")
        print()
        print("Import complete.")

    except Exception as e:
        conn.rollback()
        from errors import ForgeError
        raise ForgeError(f"Import failed: {e}")
    finally:
        conn.close()


def cmd_status(args):
    """Show what would be imported from a project directory."""
    source_dir = Path(args.source)
    if not source_dir.is_dir():
        from errors import EntityNotFound
        raise EntityNotFound(f"Source directory not found: {source_dir}")

    print(f"## Migration Status: {source_dir}")
    print()

    total = 0
    for filename, (list_key, table, prefix) in sorted(ENTITY_FILES.items()):
        path = source_dir / filename
        if not path.exists():
            continue
        data = load_json_file(path)
        if data is None:
            continue
        items = data.get(list_key, [])
        count = len(items)
        total += count
        print(f"  {filename}: {count} {table}")

        if filename == "knowledge.json":
            versions = sum(len(k.get("versions", [])) for k in items)
            links = sum(len(k.get("linked_entities", [])) for k in items)
            print(f"    -> {versions} versions, {links} entity links")

    print()
    print(f"Total entities: {total}")


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Forge Migrate — Import JSON project data into PostgreSQL"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("import", help="Import JSON data to PostgreSQL")
    p.add_argument("source", help="Path to project directory (forge_output/project)")
    p.add_argument("--database-url", help="PostgreSQL connection URL")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would be imported without making changes")

    p = sub.add_parser("status", help="Show migration status")
    p.add_argument("source", help="Path to project directory")

    args = parser.parse_args()

    commands = {
        "import": cmd_import,
        "status": cmd_status,
    }

    from errors import ForgeError
    try:
        commands[args.command](args)
    except ForgeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
