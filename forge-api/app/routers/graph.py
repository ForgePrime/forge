"""Graph API — aggregates all entity types into a node+edge graph."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_storage
from app.routers._helpers import check_project_exists, load_entity

router = APIRouter(prefix="/projects/{slug}/graph", tags=["graph"])

# Entity type → JSON file name and list key
ENTITY_SOURCES: dict[str, tuple[str, str]] = {
    "objective": ("objectives", "objectives"),
    "idea": ("ideas", "ideas"),
    "task": ("tracker", "tasks"),
    "decision": ("decisions", "decisions"),
    "knowledge": ("knowledge", "knowledge"),
    "guideline": ("guidelines", "guidelines"),
    "research": ("research", "research"),
    "lesson": ("lessons", "lessons"),
    "ac_template": ("ac_templates", "ac_templates"),
}

# Display fields per entity type (used as node.data)
DISPLAY_FIELDS: dict[str, list[str]] = {
    "objective": ["title", "status", "appetite", "scopes"],
    "idea": ["title", "status", "category", "priority"],
    "task": ["name", "status", "type", "scopes"],
    "decision": ["issue", "status", "type", "scope"],
    "knowledge": ["title", "status", "category", "scope"],
    "guideline": ["title", "status", "scope", "weight"],
    "research": ["title", "status", "category"],
    "lesson": ["title", "severity", "category"],
    "ac_template": ["title", "status", "category"],
}


def _label(entity: dict, entity_type: str) -> str:
    """Get display label for an entity."""
    return str(entity.get("title") or entity.get("name") or entity.get("issue") or entity.get("id", ""))


def _build_node(entity: dict, entity_type: str) -> dict:
    """Convert an entity dict into a graph node."""
    fields = DISPLAY_FIELDS.get(entity_type, [])
    data: dict = {"id": entity["id"], "label": _label(entity, entity_type)}
    for f in fields:
        if f in entity:
            data[f] = entity[f]
    return {
        "id": f"{entity_type}:{entity['id']}",
        "type": entity_type,
        "data": data,
    }


def _derive_edges(all_entities: dict[str, list[dict]]) -> list[dict]:
    """Derive typed edges from entity relationships."""
    edges: list[dict] = []
    seen: set[str] = set()

    def _add(source: str, target: str, edge_type: str, label: str = "") -> None:
        key = f"{source}->{target}:{edge_type}"
        if key not in seen:
            seen.add(key)
            edges.append({"source": source, "target": target, "type": edge_type, "label": label})

    # Build node ID sets for validation
    node_ids: set[str] = set()
    for etype, items in all_entities.items():
        for e in items:
            node_ids.add(f"{etype}:{e['id']}")

    # 1. depends_on: Task→Task
    for task in all_entities.get("task", []):
        for dep_id in task.get("depends_on") or []:
            src = f"task:{task['id']}"
            tgt = f"task:{dep_id}"
            if tgt in node_ids:
                _add(src, tgt, "depends_on", "depends on")

    # 2. depends_on: Idea→Idea (from relations)
    for idea in all_entities.get("idea", []):
        for rel in idea.get("relations") or []:
            if isinstance(rel, dict) and rel.get("type") == "depends_on":
                src = f"idea:{idea['id']}"
                tgt = f"idea:{rel['target_id']}"
                if tgt in node_ids:
                    _add(src, tgt, "depends_on", "depends on")

    # 3. advances_kr: Idea→Objective
    for idea in all_entities.get("idea", []):
        for akr in idea.get("advances_key_results") or []:
            # Format: "O-001/KR-1" → extract O-001
            if "/" in str(akr):
                obj_id = akr.split("/")[0]
            else:
                obj_id = akr
            src = f"idea:{idea['id']}"
            tgt = f"objective:{obj_id}"
            if tgt in node_ids:
                _add(src, tgt, "advances_kr", f"advances {akr}")

    # 4. origin: Task→Idea or Task→Objective
    for task in all_entities.get("task", []):
        origin = task.get("origin") or ""
        if origin.startswith("I-"):
            tgt = f"idea:{origin}"
            if tgt in node_ids:
                _add(f"task:{task['id']}", tgt, "origin", "from idea")
        elif origin.startswith("O-"):
            tgt = f"objective:{origin}"
            if tgt in node_ids:
                _add(f"task:{task['id']}", tgt, "origin", "from objective")

    # 5. derived_from: Guideline→Objective
    for gl in all_entities.get("guideline", []):
        derived = gl.get("derived_from") or ""
        if derived.startswith("O-"):
            src = f"guideline:{gl['id']}"
            tgt = f"objective:{derived}"
            if tgt in node_ids:
                _add(src, tgt, "derived_from", "derived from")

    return edges


@router.get("")
async def get_graph(
    slug: str,
    types: str | None = Query(None, description="Comma-separated entity types to include"),
    exclude_status: str | None = Query(None, description="Comma-separated statuses to exclude"),
    storage=Depends(get_storage),
) -> dict:
    """Return the full entity graph for a project."""
    await check_project_exists(storage, slug)

    # Determine which entity types to load
    if types:
        requested = set(t.strip() for t in types.split(","))
        requested &= set(ENTITY_SOURCES.keys())  # only valid types
    else:
        requested = set(ENTITY_SOURCES.keys())

    # Parse exclude statuses
    excluded_statuses: set[str] = set()
    if exclude_status:
        excluded_statuses = set(s.strip().upper() for s in exclude_status.split(","))

    # Load all requested entity files in parallel
    async def _load(etype: str) -> tuple[str, list[dict]]:
        file_name, list_key = ENTITY_SOURCES[etype]
        try:
            data = await load_entity(storage, slug, file_name)
            return etype, data.get(list_key, [])
        except Exception:
            return etype, []

    results = await asyncio.gather(*[_load(et) for et in requested])

    # Build nodes with filtering
    all_entities: dict[str, list[dict]] = {}
    nodes: list[dict] = []
    entity_counts: dict[str, int] = {}

    for etype, items in results:
        filtered = []
        for item in items:
            status = str(item.get("status", "")).upper()
            if excluded_statuses and status in excluded_statuses:
                continue
            filtered.append(item)
            nodes.append(_build_node(item, etype))
        all_entities[etype] = filtered
        entity_counts[etype] = len(filtered)

    # Derive edges
    edges = _derive_edges(all_entities)
    edge_counts: dict[str, int] = {}
    for e in edges:
        edge_counts[e["type"]] = edge_counts.get(e["type"], 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "entity_counts": entity_counts,
            "edge_counts": edge_counts,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
