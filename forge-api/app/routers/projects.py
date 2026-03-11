"""Projects router — CRUD + status dashboard."""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_storage
from app.routers._helpers import (
    _get_lock,
    check_project_exists,
    load_entity,
    save_entity,
)

router = APIRouter(prefix="/projects", tags=["projects"])

_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


class ProjectCreate(BaseModel):
    slug: str
    goal: str = ""
    config: dict = {}


class ProjectUpdate(BaseModel):
    goal: str | None = None
    config: dict | None = None


@router.get("")
async def list_projects(storage=Depends(get_storage)):
    """List all projects."""
    slugs = await asyncio.to_thread(storage.list_projects)
    return {"projects": slugs}


@router.post("", status_code=201)
async def create_project(body: ProjectCreate, storage=Depends(get_storage)):
    """Create a new project."""
    if not _SLUG_RE.match(body.slug):
        raise HTTPException(422, "Invalid project slug — use alphanumeric, hyphens, underscores only")
    exists = await asyncio.to_thread(storage.exists, body.slug, "tracker")
    if exists:
        raise HTTPException(409, f"Project '{body.slug}' already exists")
    data = {
        "project": body.slug,
        "goal": body.goal,
        "config": body.config,
        "tasks": [],
    }
    await save_entity(storage, body.slug, "tracker", data)
    return {"project": body.slug, "goal": body.goal}


@router.get("/{slug}")
async def get_project(slug: str, storage=Depends(get_storage)):
    """Get project by slug."""
    await check_project_exists(storage, slug)
    tracker = await load_entity(storage, slug, "tracker")
    return {
        "project": tracker.get("project", slug),
        "goal": tracker.get("goal", ""),
        "config": tracker.get("config", {}),
        "created": tracker.get("created", ""),
        "updated": tracker.get("updated", ""),
        "task_count": len(tracker.get("tasks", [])),
    }


@router.patch("/{slug}")
async def update_project(slug: str, body: ProjectUpdate, storage=Depends(get_storage)):
    """Update project goal and/or config."""
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "tracker"):
        tracker = await load_entity(storage, slug, "tracker")
        if body.goal is not None:
            tracker["goal"] = body.goal
        if body.config is not None:
            tracker["config"] = body.config
        await save_entity(storage, slug, "tracker", tracker)
    return {
        "project": tracker.get("project", slug),
        "goal": tracker.get("goal", ""),
        "config": tracker.get("config", {}),
        "created": tracker.get("created", ""),
        "updated": tracker.get("updated", ""),
        "task_count": len(tracker.get("tasks", [])),
    }


@router.get("/{slug}/status")
async def project_status(slug: str, storage=Depends(get_storage)):
    """Project dashboard — task counts, progress, blockers."""
    await check_project_exists(storage, slug)
    tracker = await load_entity(storage, slug, "tracker")
    tasks = tracker.get("tasks", [])

    status_counts = {}
    for t in tasks:
        s = t.get("status", "TODO")
        status_counts[s] = status_counts.get(s, 0) + 1

    total = len(tasks)
    done = status_counts.get("DONE", 0)

    blockers = [
        {"id": t["id"], "name": t.get("name", ""), "reason": t.get("failed_reason", "")}
        for t in tasks if t.get("status") == "FAILED"
    ]

    return {
        "project": tracker.get("project", slug),
        "goal": tracker.get("goal", ""),
        "total_tasks": total,
        "progress_pct": round(done / total * 100, 1) if total else 0,
        "status_counts": status_counts,
        "blockers": blockers,
    }
