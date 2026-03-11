"""Objectives router — CRUD + coverage dashboard."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app.dependencies import get_storage
from app.routers._helpers import (
    _get_lock,
    check_project_exists,
    find_item_or_404,
    load_entity,
    next_id,
    save_entity,
)

router = APIRouter(prefix="/projects/{slug}/objectives", tags=["objectives"])


class ObjectiveCreate(BaseModel):
    title: str
    description: str
    key_results: list[dict]
    appetite: Literal["small", "medium", "large"] = "medium"
    scope: Literal["project", "cross-project"] = "project"
    assumptions: list[str] = []
    tags: list[str] = []
    scopes: list[str] = []
    derived_guidelines: list[str] = []
    knowledge_ids: list[str] = []
    guideline_ids: list[str] = []
    relations: list[dict] = []

    @field_validator("key_results")
    @classmethod
    def validate_key_results(cls, v):
        if not v:
            raise ValueError("At least one key_result is required")
        for i, kr in enumerate(v):
            has_metric = bool(kr.get("metric")) and kr.get("target") is not None
            has_description = bool(kr.get("description"))
            if not has_metric and not has_description:
                raise ValueError(
                    f"key_result[{i}] must have either ('metric' + 'target') or 'description'"
                )
        return v


class ObjectiveUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"] | None = None
    appetite: Literal["small", "medium", "large"] | None = None
    assumptions: list[str] | None = None
    tags: list[str] | None = None
    key_results: list[dict] | None = None
    scopes: list[str] | None = None
    derived_guidelines: list[str] | None = None
    knowledge_ids: list[str] | None = None
    guideline_ids: list[str] | None = None
    relations: list[dict] | None = None


@router.get("")
async def list_objectives(
    slug: str,
    status: str | None = None,
    storage=Depends(get_storage),
):
    await check_project_exists(storage, slug)
    data = await load_entity(storage, slug, "objectives")
    objectives = data.get("objectives", [])
    if status:
        objectives = [o for o in objectives if o.get("status") == status]
    return {"objectives": objectives, "count": len(objectives)}


@router.post("", status_code=201)
async def create_objectives(slug: str, body: list[ObjectiveCreate], storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "objectives"):
        data = await load_entity(storage, slug, "objectives")
        objectives = data.get("objectives", [])
        added = []
        for item in body:
            obj_id = next_id(objectives, "O")
            obj = {**item.model_dump(), "id": obj_id, "status": "ACTIVE"}
            objectives.append(obj)
            added.append(obj_id)
        data["objectives"] = objectives
        await save_entity(storage, slug, "objectives", data)
    return {"added": added, "total": len(objectives)}


@router.get("/status")
async def objectives_coverage(slug: str, storage=Depends(get_storage)):
    """Coverage dashboard — KR progress, alignment."""
    await check_project_exists(storage, slug)
    data = await load_entity(storage, slug, "objectives")
    objectives = data.get("objectives", [])

    # Load ideas and tasks for alignment
    ideas_data = await load_entity(storage, slug, "ideas")
    tracker = await load_entity(storage, slug, "tracker")

    ideas = ideas_data.get("ideas", [])
    tasks = tracker.get("tasks", [])

    results = []
    for obj in objectives:
        obj_id = obj["id"]
        krs = obj.get("key_results", [])

        # Calculate KR progress
        kr_progress = []
        for kr in krs:
            if kr.get("metric"):
                baseline = kr.get("baseline", 0)
                target = kr.get("target", 0)
                current = kr.get("current", baseline)
                span = target - baseline
                pct = round((current - baseline) / span * 100, 1) if span else 0
                kr_progress.append({
                    "type": "numeric",
                    "metric": kr.get("metric", ""),
                    "baseline": baseline,
                    "target": target,
                    "current": current,
                    "progress_pct": min(max(pct, 0), 100),
                })
            else:
                kr_progress.append({
                    "type": "descriptive",
                    "description": kr.get("description", ""),
                    "status": kr.get("status", "NOT_STARTED"),
                })

        # Count aligned ideas and tasks
        aligned_ideas = [i for i in ideas if any(
            akr.startswith(f"{obj_id}/") for akr in i.get("advances_key_results", [])
        )]
        aligned_task_ids = set()
        for idea in aligned_ideas:
            for t in tasks:
                if t.get("origin_idea_id") == idea.get("id"):
                    aligned_task_ids.add(t["id"])

        results.append({
            "id": obj_id,
            "title": obj.get("title", ""),
            "status": obj.get("status", "ACTIVE"),
            "key_results": kr_progress,
            "aligned_ideas": len(aligned_ideas),
            "aligned_tasks": len(aligned_task_ids),
        })

    return {"objectives": results, "count": len(results)}


@router.get("/{obj_id}")
async def get_objective(slug: str, obj_id: str, storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    data = await load_entity(storage, slug, "objectives")
    return find_item_or_404(data.get("objectives", []), obj_id, "Objective")


@router.patch("/{obj_id}")
async def update_objective(slug: str, obj_id: str, body: ObjectiveUpdate, storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "objectives"):
        data = await load_entity(storage, slug, "objectives")
        obj = find_item_or_404(data.get("objectives", []), obj_id, "Objective")
        updates = body.model_dump(exclude_none=True)
        for k, v in updates.items():
            obj[k] = v
        await save_entity(storage, slug, "objectives", data)
    return obj
