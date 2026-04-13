"""
PostgreSQL Storage Adapter — implements StorageAdapter Protocol for Forge.

Translates between the dict-based interface that core modules expect
and row-based PostgreSQL storage. Core modules work unchanged — they
call load_data/save_data with entity dicts, and this adapter handles
the SQL translation.

Architecture:
  - Uses psycopg2 (sync) for compatibility with existing core modules
    (which are synchronous). The FastAPI layer uses asyncpg separately.
  - Connection pooling via psycopg2.pool.ThreadedConnectionPool.
  - Entity type → table name mapping with row↔dict converters.
  - Single-source-of-truth column registry (ColDef) — adding a column
    is a one-line change.

Reference: docs/FORGE-PLATFORM-V2.md Section 7.1
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from core.storage import (
    EntityNotFoundError,
    EntityType,
    StorageError,
    StorageWriteError,
    default_structure,
    now_iso,
)

try:
    from core.knowledge_versions import KnowledgeVersioningService
except ImportError:
    KnowledgeVersioningService = None  # type: ignore

try:
    from core.knowledge_impact import KnowledgeImpactService
except ImportError:
    KnowledgeImpactService = None  # type: ignore

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
except ImportError:
    psycopg2 = None  # type: ignore


# ---------------------------------------------------------------------------
# Column registry — single source of truth for DB ↔ JSON mapping
# ---------------------------------------------------------------------------

class ColType(Enum):
    TEXT = "text"
    INT = "int"
    BOOL = "bool"
    JSONB = "jsonb"
    TEXT_ARRAY = "text[]"
    TIMESTAMP = "timestamp"


@dataclass(frozen=True)
class ColDef:
    """Definition of a single database column and its JSON mapping.

    name:     DB column name (e.g. "ext_id", "created_at")
    col_type: PostgreSQL type category
    json_key: JSON key if different from DB name. Empty string = same as name.
              Special value "id" maps ext_id ↔ id.
    """
    name: str
    col_type: ColType
    json_key: str = ""

    @property
    def json_name(self) -> str:
        return self.json_key or self.name


class TableMeta:
    """Derived metadata for a table, computed once from its ColDef list."""

    def __init__(self, columns: list[ColDef]):
        self.columns = columns
        self.known_cols = {c.name for c in columns}
        self.jsonb_cols = {c.name for c in columns if c.col_type == ColType.JSONB}
        self.array_cols = {c.name for c in columns if c.col_type == ColType.TEXT_ARRAY}
        self.ts_cols = {c.name for c in columns if c.col_type == ColType.TIMESTAMP}
        self.has_updated_at = "updated_at" in self.known_cols
        # JSON key → DB column (for keys that differ)
        self.json_to_db = {
            c.json_key: c.name
            for c in columns
            if c.json_key and c.json_key != c.name
        }
        # DB column → JSON key (for keys that differ)
        self.db_to_json = {
            c.name: c.json_key
            for c in columns
            if c.json_key and c.json_key != c.name
        }


# ---------------------------------------------------------------------------
# Per-table column definitions
# ---------------------------------------------------------------------------

_TASKS_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("name", ColType.TEXT),
    ColDef("description", ColType.TEXT),
    ColDef("instruction", ColType.TEXT),
    ColDef("type", ColType.TEXT),
    ColDef("status", ColType.TEXT),
    ColDef("origin", ColType.TEXT),
    ColDef("origin_idea_id", ColType.TEXT),
    ColDef("skill", ColType.TEXT),
    ColDef("parallel", ColType.BOOL),
    ColDef("acceptance_criteria", ColType.JSONB),
    ColDef("test_requirements", ColType.JSONB),
    ColDef("depends_on", ColType.TEXT_ARRAY),
    ColDef("conflicts_with", ColType.TEXT_ARRAY),
    ColDef("knowledge_ids", ColType.TEXT_ARRAY),
    ColDef("scopes", ColType.TEXT_ARRAY),
    ColDef("blocked_by_decisions", ColType.TEXT_ARRAY),
    ColDef("agent", ColType.TEXT),
    ColDef("failed_reason", ColType.TEXT),
    ColDef("started_at", ColType.TIMESTAMP),
    ColDef("completed_at", ColType.TIMESTAMP),
    ColDef("created_at", ColType.TIMESTAMP),
    ColDef("updated_at", ColType.TIMESTAMP),
]

_DECISIONS_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("task_id", ColType.TEXT),
    ColDef("type", ColType.TEXT),
    ColDef("status", ColType.TEXT),
    ColDef("issue", ColType.TEXT),
    ColDef("recommendation", ColType.TEXT),
    ColDef("reasoning", ColType.TEXT),
    ColDef("alternatives", ColType.JSONB),
    ColDef("confidence", ColType.TEXT),
    ColDef("decided_by", ColType.TEXT),
    ColDef("file", ColType.TEXT),
    ColDef("scope", ColType.TEXT),
    ColDef("tags", ColType.TEXT_ARRAY),
    ColDef("exploration_type", ColType.TEXT),
    ColDef("findings", ColType.JSONB),
    ColDef("options", ColType.JSONB),
    ColDef("open_questions", ColType.JSONB),
    ColDef("severity", ColType.TEXT),
    ColDef("likelihood", ColType.TEXT),
    ColDef("linked_entity_type", ColType.TEXT),
    ColDef("linked_entity_id", ColType.TEXT),
    ColDef("mitigation_plan", ColType.TEXT),
    ColDef("resolution_notes", ColType.TEXT),
    ColDef("blockers", ColType.JSONB),
    ColDef("ready_for_tracker", ColType.BOOL),
    ColDef("evidence_refs", ColType.JSONB),
    ColDef("created_at", ColType.TIMESTAMP, json_key="timestamp"),
    ColDef("updated_at", ColType.TIMESTAMP),
]

_CHANGES_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("task_id", ColType.TEXT),
    ColDef("file", ColType.TEXT),
    ColDef("action", ColType.TEXT),
    ColDef("summary", ColType.TEXT),
    ColDef("reasoning_trace", ColType.JSONB),
    ColDef("decision_ids", ColType.TEXT_ARRAY),
    ColDef("guidelines_checked", ColType.TEXT_ARRAY),
    ColDef("group_id", ColType.TEXT),
    ColDef("lines_added", ColType.INT),
    ColDef("lines_removed", ColType.INT),
    ColDef("recorded_at", ColType.TIMESTAMP, json_key="timestamp"),
]

_GUIDELINES_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("title", ColType.TEXT),
    ColDef("scope", ColType.TEXT),
    ColDef("content", ColType.TEXT),
    ColDef("rationale", ColType.TEXT),
    ColDef("examples", ColType.JSONB),
    ColDef("tags", ColType.TEXT_ARRAY),
    ColDef("weight", ColType.TEXT),
    ColDef("status", ColType.TEXT),
    ColDef("derived_from", ColType.TEXT),
    ColDef("imported_from", ColType.TEXT),
    ColDef("promoted_from", ColType.TEXT),
    ColDef("created_at", ColType.TIMESTAMP, json_key="created"),
    ColDef("updated_at", ColType.TIMESTAMP, json_key="updated"),
]

_IDEAS_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("parent_id", ColType.TEXT),
    ColDef("title", ColType.TEXT),
    ColDef("description", ColType.TEXT),
    ColDef("category", ColType.TEXT),
    ColDef("status", ColType.TEXT),
    ColDef("appetite", ColType.TEXT),
    ColDef("priority", ColType.TEXT),
    ColDef("tags", ColType.TEXT_ARRAY),
    ColDef("scopes", ColType.TEXT_ARRAY),
    ColDef("knowledge_ids", ColType.TEXT_ARRAY),
    ColDef("guidelines", ColType.TEXT_ARRAY),
    ColDef("advances_key_results", ColType.TEXT_ARRAY),
    ColDef("rejection_reason", ColType.TEXT),
    ColDef("merged_into", ColType.TEXT),
    ColDef("exploration_notes", ColType.TEXT),
    ColDef("committed_at", ColType.TIMESTAMP),
    ColDef("created_at", ColType.TIMESTAMP, json_key="created"),
    ColDef("updated_at", ColType.TIMESTAMP, json_key="updated"),
]

_OBJECTIVES_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("title", ColType.TEXT),
    ColDef("description", ColType.TEXT),
    ColDef("appetite", ColType.TEXT),
    ColDef("scope", ColType.TEXT),
    ColDef("status", ColType.TEXT),
    ColDef("assumptions", ColType.JSONB),
    ColDef("tags", ColType.TEXT_ARRAY),
    ColDef("scopes", ColType.TEXT_ARRAY),
    ColDef("derived_guidelines", ColType.TEXT_ARRAY),
    ColDef("knowledge_ids", ColType.TEXT_ARRAY),
    ColDef("created_at", ColType.TIMESTAMP, json_key="created"),
    ColDef("updated_at", ColType.TIMESTAMP, json_key="updated"),
]

_LESSONS_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("category", ColType.TEXT),
    ColDef("title", ColType.TEXT),
    ColDef("detail", ColType.TEXT),
    ColDef("task_id", ColType.TEXT),
    ColDef("decision_ids", ColType.TEXT_ARRAY),
    ColDef("severity", ColType.TEXT),
    ColDef("applies_to", ColType.TEXT),
    ColDef("tags", ColType.TEXT_ARRAY),
    ColDef("promoted_to_guideline", ColType.TEXT),
    ColDef("promoted_to_knowledge", ColType.TEXT),
    ColDef("created_at", ColType.TIMESTAMP, json_key="timestamp"),
]

_KNOWLEDGE_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("title", ColType.TEXT),
    ColDef("category", ColType.TEXT),
    ColDef("content", ColType.TEXT),
    ColDef("current_version", ColType.INT),
    ColDef("status", ColType.TEXT),
    ColDef("scopes", ColType.TEXT_ARRAY),
    ColDef("tags", ColType.TEXT_ARRAY),
    ColDef("dependencies", ColType.TEXT_ARRAY),
    ColDef("source", ColType.JSONB),
    ColDef("source_type", ColType.TEXT),
    ColDef("created_by", ColType.TEXT),
    ColDef("linked_entities", ColType.JSONB),
    ColDef("review", ColType.JSONB),
    ColDef("created_at", ColType.TIMESTAMP),
    ColDef("updated_at", ColType.TIMESTAMP),
]

_AC_TEMPLATES_COLS = [
    ColDef("ext_id", ColType.TEXT, json_key="id"),
    ColDef("title", ColType.TEXT),
    ColDef("description", ColType.TEXT),
    ColDef("template", ColType.TEXT),
    ColDef("category", ColType.TEXT),
    ColDef("verification_method", ColType.TEXT),
    ColDef("parameters", ColType.JSONB),
    ColDef("scopes", ColType.TEXT_ARRAY),
    ColDef("tags", ColType.TEXT_ARRAY),
    ColDef("status", ColType.TEXT),
    ColDef("usage_count", ColType.INT),
    ColDef("created_at", ColType.TIMESTAMP),
    ColDef("updated_at", ColType.TIMESTAMP),
]


# ---------------------------------------------------------------------------
# Build derived metadata from column definitions
# ---------------------------------------------------------------------------

_TABLE_META: dict[str, TableMeta] = {
    "tasks": TableMeta(_TASKS_COLS),
    "decisions": TableMeta(_DECISIONS_COLS),
    "changes": TableMeta(_CHANGES_COLS),
    "guidelines": TableMeta(_GUIDELINES_COLS),
    "ideas": TableMeta(_IDEAS_COLS),
    "objectives": TableMeta(_OBJECTIVES_COLS),
    "lessons": TableMeta(_LESSONS_COLS),
    "knowledge": TableMeta(_KNOWLEDGE_COLS),
    "ac_templates": TableMeta(_AC_TEMPLATES_COLS),
}


# ---------------------------------------------------------------------------
# Entity → Table mapping
# ---------------------------------------------------------------------------

_ENTITY_TABLE_MAP: dict[str, tuple[str, str]] = {
    EntityType.TRACKER: ("tasks", "tasks"),
    EntityType.DECISIONS: ("decisions", "decisions"),
    EntityType.CHANGES: ("changes", "changes"),
    EntityType.GUIDELINES: ("guidelines", "guidelines"),
    EntityType.IDEAS: ("ideas", "ideas"),
    EntityType.OBJECTIVES: ("objectives", "objectives"),
    EntityType.LESSONS: ("lessons", "lessons"),
    EntityType.KNOWLEDGE: ("knowledge", "knowledge"),
    EntityType.AC_TEMPLATES: ("ac_templates", "ac_templates"),
}


# ---------------------------------------------------------------------------
# Row ↔ Dict converters (metadata-driven)
# ---------------------------------------------------------------------------

def _row_to_dict(row: dict, entity_type: str) -> dict:
    """Convert a database row to JSON-compatible dict.

    Uses TableMeta to determine key mapping, timestamp conversion, etc.
    """
    table = entity_type
    if isinstance(entity_type, EntityType):
        table = _ENTITY_TABLE_MAP.get(entity_type, (entity_type, ""))[0]

    meta = _TABLE_META.get(table)
    if meta is None:
        return dict(row)

    result = {}
    for key, value in row.items():
        if key == "project_id":
            continue
        if key == "ext_id":
            result["id"] = value
            continue
        if key == "id":
            result["_db_id"] = value
            continue
        if key in meta.ts_cols and value is not None:
            ts_str = value.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(value, datetime) else str(value)
            out_key = meta.db_to_json.get(key, key)
            result[out_key] = ts_str
            continue
        if key in meta.ts_cols and value is None:
            out_key = meta.db_to_json.get(key, key)
            result[out_key] = value
            continue
        result[key] = value

    return result


def _dict_to_row(item: dict, entity_type: str, project_id: int) -> dict:
    """Convert a JSON-format dict to database row columns.

    Uses TableMeta for key mapping, JSONB serialization, and column filtering.
    """
    table = entity_type
    if isinstance(entity_type, EntityType):
        table = _ENTITY_TABLE_MAP.get(entity_type, (entity_type, ""))[0]

    meta = _TABLE_META.get(table)
    row = {"project_id": project_id}

    if meta is None:
        row.update(item)
        return row

    for key, value in item.items():
        if key in ("_db_id", "project"):
            continue
        if key == "id":
            row["ext_id"] = value
            continue
        # Map JSON key → DB column (e.g. "timestamp" → "recorded_at")
        if key in meta.json_to_db:
            row[meta.json_to_db[key]] = value
            continue
        # JSONB: serialize non-string values
        if key in meta.jsonb_cols and value is not None:
            row[key] = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            continue
        row[key] = value

    # Filter out unknown columns
    allowed = meta.known_cols | {"project_id", "ext_id"}
    return {k: v for k, v in row.items() if k in allowed}


# ---------------------------------------------------------------------------
# Tracker-specific handling
# ---------------------------------------------------------------------------

def _tracker_rows_to_dict(rows: list[dict], project: str, project_row: Optional[dict]) -> dict:
    """Convert task rows + project row into the tracker dict format."""
    tasks = [_row_to_dict(r, "tasks") for r in rows]
    for t in tasks:
        t.pop("_db_id", None)

    result = {
        "project": project,
        "goal": project_row.get("goal", "") if project_row else "",
        "created": "",
        "updated": "",
        "config": {},
        "tasks": tasks,
    }

    if project_row:
        if project_row.get("created_at"):
            ts = project_row["created_at"]
            result["created"] = ts.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(ts, datetime) else str(ts)
        if project_row.get("updated_at"):
            ts = project_row["updated_at"]
            result["updated"] = ts.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(ts, datetime) else str(ts)
        if project_row.get("config"):
            result["config"] = project_row["config"] if isinstance(project_row["config"], dict) else json.loads(project_row["config"])

    return result


def _entity_rows_to_dict(rows: list[dict], entity_type: str, project: str, list_key: str) -> dict:
    """Convert entity rows into the standard JSON dict format."""
    items = [_row_to_dict(r, entity_type) for r in rows]
    for item in items:
        item.pop("_db_id", None)

    result = {
        "project": project,
        "updated": now_iso(),
        list_key: items,
    }

    if entity_type == EntityType.DECISIONS:
        result["open_count"] = sum(1 for i in items if i.get("status") == "OPEN")

    return result


# ---------------------------------------------------------------------------
# PostgreSQL Storage Adapter
# ---------------------------------------------------------------------------

class PostgreSQLAdapter:
    """Storage backend using PostgreSQL.

    Implements the same StorageAdapter Protocol as JSONFileStorage.
    Core modules call load_data/save_data and get the same dict format.
    """

    def __init__(self, database_url: Optional[str] = None, min_conn: int = 1, max_conn: int = 5) -> None:
        if psycopg2 is None:
            raise ImportError("psycopg2 or psycopg required for PostgreSQLAdapter")

        self._database_url = database_url or os.environ.get(
            "DATABASE_URL", "postgresql://forge:forge@localhost:5432/forge_db"
        )
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            min_conn, max_conn, self._database_url
        )
        self._versioning: Optional[KnowledgeVersioningService] = None
        if KnowledgeVersioningService is not None:
            self._versioning = KnowledgeVersioningService(self._pool)
        self._impact: Optional[KnowledgeImpactService] = None
        if KnowledgeImpactService is not None:
            self._impact = KnowledgeImpactService(self._pool)

    @contextmanager
    def _conn(self):
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def _get_project_id(self, cur, project: str) -> Optional[int]:
        cur.execute("SELECT id FROM projects WHERE slug = %s", (project,))
        row = cur.fetchone()
        return row["id"] if row else None

    def _ensure_project(self, cur, project: str) -> int:
        pid = self._get_project_id(cur, project)
        if pid is not None:
            return pid
        cur.execute(
            "INSERT INTO projects (slug) VALUES (%s) RETURNING id",
            (project,),
        )
        return cur.fetchone()["id"]

    def _get_knowledge_db_id(self, cur, pid: int, ext_id: str) -> Optional[int]:
        cur.execute(
            "SELECT id FROM knowledge WHERE project_id = %s AND ext_id = %s",
            (pid, ext_id),
        )
        row = cur.fetchone()
        return row["id"] if row else None

    # -------------------------------------------------------------------
    # load_data
    # -------------------------------------------------------------------

    def load_data(self, project: str, entity: str) -> dict:
        entity_key = EntityType(entity) if isinstance(entity, str) else entity
        table, list_key = _ENTITY_TABLE_MAP[entity_key]

        with self._conn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    pid = self._get_project_id(cur, project)
                    if pid is None:
                        return default_structure(entity, project)

                    if entity_key == EntityType.TRACKER:
                        cur.execute("SELECT * FROM projects WHERE id = %s", (pid,))
                        project_row = cur.fetchone()
                        cur.execute(
                            "SELECT * FROM tasks WHERE project_id = %s ORDER BY ext_id",
                            (pid,),
                        )
                        rows = cur.fetchall()
                        return _tracker_rows_to_dict(rows, project, project_row)

                    cur.execute(
                        f"SELECT * FROM {table} WHERE project_id = %s ORDER BY ext_id",
                        (pid,),
                    )
                    rows = cur.fetchall()
                    return _entity_rows_to_dict(rows, entity_key, project, list_key)
            finally:
                conn.rollback()

    # -------------------------------------------------------------------
    # save_data
    # -------------------------------------------------------------------

    def save_data(self, project: str, entity: str, data: dict) -> None:
        entity_key = EntityType(entity) if isinstance(entity, str) else entity
        table, list_key = _ENTITY_TABLE_MAP[entity_key]
        data["updated"] = now_iso()

        with self._conn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    pid = self._ensure_project(cur, project)

                    if entity_key == EntityType.TRACKER:
                        self._save_tracker(cur, pid, project, data)
                    else:
                        self._save_entity_list(cur, pid, table, list_key, data)

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise StorageWriteError(f"Failed to save {entity} for {project}: {e}") from e

    def _save_tracker(self, cur, pid: int, project: str, data: dict) -> None:
        config = data.get("config", {})
        goal = data.get("goal", "")
        cur.execute(
            "UPDATE projects SET goal = %s, config = %s, updated_at = NOW() WHERE id = %s",
            (goal, json.dumps(config, ensure_ascii=False), pid),
        )

        tasks = data.get("tasks", [])
        cur.execute("SELECT ext_id FROM tasks WHERE project_id = %s", (pid,))
        existing = {row["ext_id"] for row in cur.fetchall()}

        for task in tasks:
            ext_id = task.get("id", "")
            if not ext_id:
                continue

            row = _dict_to_row(task, "tasks", pid)
            row.pop("project_id", None)

            if ext_id in existing:
                sets = []
                vals = []
                for k, v in row.items():
                    if k == "ext_id":
                        continue
                    sets.append(f"{k} = %s")
                    vals.append(v)
                if sets:
                    vals.append(pid)
                    vals.append(ext_id)
                    cur.execute(
                        f"UPDATE tasks SET {', '.join(sets)}, updated_at = NOW() "
                        f"WHERE project_id = %s AND ext_id = %s",
                        vals,
                    )
            else:
                row["project_id"] = pid
                cols = list(row.keys())
                placeholders = ["%s"] * len(cols)
                cur.execute(
                    f"INSERT INTO tasks ({', '.join(cols)}) VALUES ({', '.join(placeholders)})",
                    [row[c] for c in cols],
                )
                existing.add(ext_id)

        data_ext_ids = {t.get("id", "") for t in tasks}
        removed = existing - data_ext_ids
        if removed:
            cur.execute(
                "DELETE FROM tasks WHERE project_id = %s AND ext_id = ANY(%s)",
                (pid, list(removed)),
            )

    def _save_entity_list(self, cur, pid: int, table: str, list_key: str, data: dict) -> None:
        items = data.get(list_key, [])
        is_knowledge = table == "knowledge"
        meta = _TABLE_META.get(table)

        existing_content: dict[str, str] = {}
        if is_knowledge and self._versioning:
            cur.execute(
                "SELECT ext_id, content FROM knowledge WHERE project_id = %s",
                (pid,),
            )
            existing_content = {r["ext_id"]: (r["content"] or "") for r in cur.fetchall()}

        cur.execute(f"SELECT ext_id FROM {table} WHERE project_id = %s", (pid,))
        existing = {row["ext_id"] for row in cur.fetchall()}

        for item in items:
            ext_id = item.get("id", "")
            if not ext_id:
                continue

            row = _dict_to_row(item, table, pid)
            row.pop("project_id", None)

            if ext_id in existing:
                sets = []
                vals = []
                for k, v in row.items():
                    if k == "ext_id":
                        continue
                    sets.append(f"{k} = %s")
                    vals.append(v)
                if sets:
                    update_suffix = ", updated_at = NOW()" if meta and meta.has_updated_at else ""
                    vals.append(pid)
                    vals.append(ext_id)
                    cur.execute(
                        f"UPDATE {table} SET {', '.join(sets)}{update_suffix} "
                        f"WHERE project_id = %s AND ext_id = %s",
                        vals,
                    )

                if is_knowledge and self._versioning:
                    new_content = item.get("content", "")
                    old_content = existing_content.get(ext_id, "")
                    if new_content != old_content:
                        db_id = self._get_knowledge_db_id(cur, pid, ext_id)
                        if db_id is not None:
                            self._versioning.create_version(
                                knowledge_db_id=db_id,
                                content=new_content,
                                changed_by="storage_pg",
                                change_reason="Content updated via save_data",
                                conn=cur.connection,
                            )
            else:
                row["project_id"] = pid
                cols = list(row.keys())
                placeholders = ["%s"] * len(cols)
                cur.execute(
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})",
                    [row[c] for c in cols],
                )
                existing.add(ext_id)

                if is_knowledge and self._versioning:
                    db_id = self._get_knowledge_db_id(cur, pid, ext_id)
                    if db_id is not None:
                        self._versioning.ensure_initial_version(
                            knowledge_db_id=db_id,
                            content=item.get("content", ""),
                            conn=cur.connection,
                        )

        data_ext_ids = {i.get("id", "") for i in items}
        removed = existing - data_ext_ids
        if removed:
            cur.execute(
                f"DELETE FROM {table} WHERE project_id = %s AND ext_id = ANY(%s)",
                (pid, list(removed)),
            )

    # -------------------------------------------------------------------
    # exists
    # -------------------------------------------------------------------

    def exists(self, project: str, entity: str) -> bool:
        entity_key = EntityType(entity) if isinstance(entity, str) else entity
        table, _ = _ENTITY_TABLE_MAP[entity_key]

        with self._conn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    pid = self._get_project_id(cur, project)
                    if pid is None:
                        return False
                    if entity_key == EntityType.TRACKER:
                        return True
                    cur.execute(
                        f"SELECT EXISTS(SELECT 1 FROM {table} WHERE project_id = %s) AS e",
                        (pid,),
                    )
                    return cur.fetchone()["e"]
            finally:
                conn.rollback()

    # -------------------------------------------------------------------
    # list_projects
    # -------------------------------------------------------------------

    def list_projects(self) -> list[str]:
        with self._conn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT slug FROM projects ORDER BY slug")
                    return [row["slug"] for row in cur.fetchall()]
            finally:
                conn.rollback()

    # -------------------------------------------------------------------
    # load_global / save_global
    # -------------------------------------------------------------------

    def load_global(self, entity: str) -> dict:
        entity_key = EntityType(entity) if isinstance(entity, str) else entity
        table, list_key = _ENTITY_TABLE_MAP[entity_key]

        with self._conn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT * FROM {table} WHERE project_id IS NULL ORDER BY ext_id",
                        (),
                    )
                    rows = cur.fetchall()
                    items = [_row_to_dict(r, entity_key) for r in rows]
                    for item in items:
                        item.pop("_db_id", None)
                    return {
                        "project": "_global",
                        "updated": now_iso(),
                        list_key: items,
                    }
            finally:
                conn.rollback()

    def save_global(self, entity: str, data: dict) -> None:
        entity_key = EntityType(entity) if isinstance(entity, str) else entity
        table, list_key = _ENTITY_TABLE_MAP[entity_key]
        data["updated"] = now_iso()

        with self._conn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    items = data.get(list_key, [])

                    cur.execute(
                        f"SELECT ext_id FROM {table} WHERE project_id IS NULL",
                        (),
                    )
                    existing = {row["ext_id"] for row in cur.fetchall()}

                    for item in items:
                        ext_id = item.get("id", "")
                        if not ext_id:
                            continue

                        row = _dict_to_row(item, table, 0)
                        row.pop("project_id", None)

                        if ext_id in existing:
                            sets = []
                            vals = []
                            for k, v in row.items():
                                if k == "ext_id":
                                    continue
                                sets.append(f"{k} = %s")
                                vals.append(v)
                            if sets:
                                vals.append(ext_id)
                                cur.execute(
                                    f"UPDATE {table} SET {', '.join(sets)} "
                                    f"WHERE project_id IS NULL AND ext_id = %s",
                                    vals,
                                )
                        else:
                            cols = ["ext_id"] + [k for k in row.keys() if k != "ext_id"]
                            vals = [row.get(c) for c in cols]
                            col_str = "project_id, " + ", ".join(cols)
                            val_str = "NULL, " + ", ".join(["%s"] * len(cols))
                            cur.execute(
                                f"INSERT INTO {table} ({col_str}) VALUES ({val_str})",
                                vals,
                            )
                            existing.add(ext_id)

                    data_ext_ids = {i.get("id", "") for i in items}
                    removed = existing - data_ext_ids
                    if removed:
                        cur.execute(
                            f"DELETE FROM {table} WHERE project_id IS NULL AND ext_id = ANY(%s)",
                            (list(removed),),
                        )

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise StorageWriteError(f"Failed to save global {entity}: {e}") from e

    # -------------------------------------------------------------------
    # Knowledge impact analysis
    # -------------------------------------------------------------------

    def analyze_knowledge_impact(self, project: str, knowledge_ext_id: str) -> dict:
        if self._impact is None:
            return {
                "knowledge_id": None,
                "knowledge_ext_id": knowledge_ext_id,
                "title": "",
                "total_affected": 0,
                "impact_summary": {"high": 0, "medium": 0, "low": 0},
                "affected_entities": [],
                "error": "Impact analysis service not available",
            }

        with self._conn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    pid = self._get_project_id(cur, project)
                    if pid is None:
                        raise ValueError(f"Project '{project}' not found")

                    cur.execute(
                        "SELECT id FROM knowledge "
                        "WHERE (project_id = %s OR project_id IS NULL) AND ext_id = %s "
                        "ORDER BY CASE WHEN project_id = %s THEN 0 ELSE 1 END "
                        "LIMIT 1",
                        (pid, knowledge_ext_id, pid),
                    )
                    row = cur.fetchone()
                    if row is None:
                        raise ValueError(
                            f"Knowledge '{knowledge_ext_id}' not found in project '{project}'"
                        )

                    return self._impact.analyze_impact(
                        row["id"], pid, cur=cur
                    )
            finally:
                conn.rollback()

    # -------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()
            self._pool = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __repr__(self) -> str:
        return f"PostgreSQLAdapter(url='{self._database_url[:30]}...')"
