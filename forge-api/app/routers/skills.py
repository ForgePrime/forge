"""Skills router — CRUD for global platform skills (no project slug)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.dependencies import get_storage
from app.routers._helpers import (
    _get_lock,
    emit_event,
    find_item_or_404,
    load_entity,
    next_id,
    save_entity,
)

router = APIRouter(prefix="/skills", tags=["skills"])

# ---------------------------------------------------------------------------
# Storage key — skills are global (no project slug)
# ---------------------------------------------------------------------------
_GLOBAL = "__global__"
_ENTITY = "skills"

VALID_CATEGORIES = [
    "workflow", "analysis", "generation", "validation",
    "integration", "refactoring", "testing", "deployment",
    "documentation", "custom",
]
VALID_STATUSES = ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SkillCreate(BaseModel):
    name: str
    description: str = ""
    category: Literal[
        "workflow", "analysis", "generation", "validation",
        "integration", "refactoring", "testing", "deployment",
        "documentation", "custom",
    ] = "custom"
    skill_md_content: str | None = None
    evals_json: list[dict] = []
    resources: dict = {}
    teslint_config: dict | None = None
    tags: list[str] = []
    scopes: list[str] = []
    created_by: str | None = None


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: Literal[
        "workflow", "analysis", "generation", "validation",
        "integration", "refactoring", "testing", "deployment",
        "documentation", "custom",
    ] | None = None
    status: Literal["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"] | None = None
    skill_md_content: str | None = None
    evals_json: list[dict] | None = None
    resources: dict | None = None
    teslint_config: dict | None = None
    tags: list[str] | None = None
    scopes: list[str] | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_data(data: dict) -> dict:
    """Ensure skills data has proper structure."""
    if "skills" not in data:
        data["skills"] = []
    return data


def _matches_filter(skill: dict, **filters) -> bool:
    """Check if skill matches all given filters."""
    for key, value in filters.items():
        if value is None:
            continue
        if key == "search":
            q = value.lower()
            if q not in skill.get("name", "").lower() and q not in skill.get("description", "").lower():
                return False
        elif key == "tags":
            skill_tags = set(skill.get("tags", []))
            if not skill_tags.intersection(value):
                return False
        elif key == "scopes":
            skill_scopes = set(skill.get("scopes", []))
            if not skill_scopes.intersection(value):
                return False
        elif key in ("category", "status"):
            if skill.get(key) != value:
                return False
    return True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_skills(
    category: str | None = Query(None),
    status: str | None = Query(None),
    tags: str | None = Query(None, description="Comma-separated tag filter"),
    scopes: str | None = Query(None, description="Comma-separated scope filter"),
    search: str | None = Query(None, description="Search name/description"),
    storage=Depends(get_storage),
):
    """List all skills with optional filters."""
    data = await load_entity(storage, _GLOBAL, _ENTITY)
    data = _ensure_data(data)
    skills = data["skills"]

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    scope_list = [s.strip() for s in scopes.split(",")] if scopes else None

    filtered = [
        s for s in skills
        if _matches_filter(s, category=category, status=status,
                           tags=tag_list, scopes=scope_list, search=search)
    ]

    return {"skills": filtered, "count": len(filtered)}


@router.post("", status_code=201)
async def create_skills(
    body: list[SkillCreate],
    request: Request,
    storage=Depends(get_storage),
):
    """Batch create skills. Returns generated IDs."""
    if not body:
        raise HTTPException(422, "At least one skill is required")

    added = []
    async with _get_lock(_GLOBAL, _ENTITY):
        data = await load_entity(storage, _GLOBAL, _ENTITY)
        data = _ensure_data(data)
        skills = data["skills"]

        for item in body:
            skill_id = next_id(skills, "S")
            now = _now_iso()
            skill = {
                "id": skill_id,
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "status": "DRAFT",
                "skill_md_content": item.skill_md_content,
                "evals_json": item.evals_json,
                "resources": item.resources,
                "teslint_config": item.teslint_config,
                "tags": item.tags,
                "scopes": item.scopes,
                "promoted_with_warnings": False,
                "promotion_history": [],
                "usage_count": 0,
                "created_by": item.created_by,
                "created_at": now,
                "updated_at": now,
            }
            skills.append(skill)
            added.append(skill_id)

        await save_entity(storage, _GLOBAL, _ENTITY, data)

    for sid in added:
        await emit_event(request, _GLOBAL, "skill.created", {"id": sid})

    return {"added": added, "total": len(data["skills"])}


@router.get("/{skill_id}")
async def get_skill(skill_id: str, storage=Depends(get_storage)):
    """Get a single skill by ID."""
    data = await load_entity(storage, _GLOBAL, _ENTITY)
    data = _ensure_data(data)
    skill = find_item_or_404(data["skills"], skill_id, "Skill")
    return skill


@router.patch("/{skill_id}")
async def update_skill(
    skill_id: str,
    body: SkillUpdate,
    request: Request,
    storage=Depends(get_storage),
):
    """Update a skill. Status transitions validated."""
    async with _get_lock(_GLOBAL, _ENTITY):
        data = await load_entity(storage, _GLOBAL, _ENTITY)
        data = _ensure_data(data)
        skill = find_item_or_404(data["skills"], skill_id, "Skill")

        updates = body.model_dump(exclude_none=True)
        if not updates:
            return skill

        # Status transition validation
        # NOTE: DRAFT→ACTIVE is NOT allowed via PATCH — use POST /skills/{id}/promote
        # which enforces gates (valid SKILL.md, evals, TESLint). See G-015, T-082.
        if "status" in updates:
            new_status = updates["status"]
            current = skill.get("status", "DRAFT")
            valid_transitions = {
                "DRAFT": {"DEPRECATED"},
                "ACTIVE": {"DEPRECATED"},
                "DEPRECATED": {"ARCHIVED", "ACTIVE"},
                "ARCHIVED": set(),
            }
            if new_status not in valid_transitions.get(current, set()):
                raise HTTPException(
                    422,
                    f"Cannot transition from {current} to {new_status}. "
                    f"Valid: {valid_transitions.get(current, set())}",
                )

        for key, value in updates.items():
            skill[key] = value
        skill["updated_at"] = _now_iso()

        await save_entity(storage, _GLOBAL, _ENTITY, data)

    await emit_event(request, _GLOBAL, "skill.updated", {"id": skill_id})
    return skill


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    request: Request,
    storage=Depends(get_storage),
):
    """Delete a skill. Blocked if used by IN_PROGRESS tasks."""
    async with _get_lock(_GLOBAL, _ENTITY):
        data = await load_entity(storage, _GLOBAL, _ENTITY)
        data = _ensure_data(data)
        skill = find_item_or_404(data["skills"], skill_id, "Skill")

        # Check usage: scan all projects for IN_PROGRESS tasks referencing this skill
        # For now, check usage_count as a guard
        if skill.get("status") == "ACTIVE" and skill.get("usage_count", 0) > 0:
            raise HTTPException(
                409,
                f"Cannot delete ACTIVE skill '{skill_id}' with {skill['usage_count']} tasks using it. "
                "Set status to DEPRECATED first.",
            )

        data["skills"] = [s for s in data["skills"] if s.get("id") != skill_id]
        await save_entity(storage, _GLOBAL, _ENTITY, data)

    await emit_event(request, _GLOBAL, "skill.deleted", {"id": skill_id})
    return {"removed": skill_id}
