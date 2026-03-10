"""Lessons router — CRUD + promote."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_storage
from app.routers._helpers import (
    _get_lock,
    check_project_exists,
    find_item_or_404,
    load_entity,
    next_id,
    save_entity,
)

router = APIRouter(prefix="/projects/{slug}/lessons", tags=["lessons"])

LESSON_CATEGORIES = Literal[
    "pattern-discovered", "mistake-avoided", "decision-validated",
    "decision-reversed", "tool-insight", "architecture-lesson",
    "process-improvement", "market-insight",
]


class LessonCreate(BaseModel):
    category: LESSON_CATEGORIES
    title: str
    detail: str
    task_id: str = ""
    decision_ids: list[str] = []
    severity: Literal["critical", "important", "minor"] = "important"
    applies_to: str = ""
    tags: list[str] = []


class LessonPromote(BaseModel):
    target: Literal["guideline", "knowledge"] = "guideline"
    scope: str = ""
    weight: Literal["must", "should", "may"] = "should"
    # Knowledge-specific
    category: str = ""
    scopes: list[str] = []


@router.get("")
async def list_lessons(
    slug: str,
    category: str | None = None,
    severity: str | None = None,
    storage=Depends(get_storage),
):
    await check_project_exists(storage, slug)
    data = await load_entity(storage, slug, "lessons")
    lessons = data.get("lessons", [])
    if category:
        lessons = [l for l in lessons if l.get("category") == category]
    if severity:
        lessons = [l for l in lessons if l.get("severity") == severity]
    return {"lessons": lessons, "count": len(lessons)}


@router.post("", status_code=201)
async def add_lessons(slug: str, body: list[LessonCreate], storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "lessons"):
        data = await load_entity(storage, slug, "lessons")
        lessons = data.get("lessons", [])
        added = []
        for item in body:
            lesson_id = next_id(lessons, "L")
            lesson = {**item.model_dump(), "id": lesson_id, "project": slug}
            lessons.append(lesson)
            added.append(lesson_id)
        data["lessons"] = lessons
        await save_entity(storage, slug, "lessons", data)
    return {"added": added, "total": len(lessons)}


@router.get("/{lesson_id}")
async def get_lesson(slug: str, lesson_id: str, storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    data = await load_entity(storage, slug, "lessons")
    return find_item_or_404(data.get("lessons", []), lesson_id, "Lesson")


@router.post("/{lesson_id}/promote")
async def promote_lesson(
    slug: str,
    lesson_id: str,
    body: LessonPromote | None = None,
    storage=Depends(get_storage),
):
    """Promote lesson to guideline or knowledge."""
    await check_project_exists(storage, slug)
    target = body.target if body else "guideline"

    if target == "guideline":
        # Lock both lessons and global guidelines
        async with _get_lock(slug, "lessons"):
            data = await load_entity(storage, slug, "lessons")
            lesson = find_item_or_404(data.get("lessons", []), lesson_id, "Lesson")

            if lesson.get("promoted_to_guideline"):
                raise HTTPException(422, f"Already promoted to {lesson['promoted_to_guideline']}")

            # Load global guidelines
            g_data = await asyncio.to_thread(storage.load_global, "guidelines")
            guidelines = g_data.get("guidelines", [])

            guideline_id = next_id(guidelines, "G")
            guideline = {
                "id": guideline_id,
                "title": lesson["title"],
                "content": lesson["detail"],
                "scope": body.scope if body else "",
                "weight": body.weight if body else "should",
                "status": "ACTIVE",
                "promoted_from": lesson["id"],
            }
            guidelines.append(guideline)
            g_data["guidelines"] = guidelines
            await asyncio.to_thread(storage.save_global, "guidelines", g_data)

            lesson["promoted_to_guideline"] = guideline_id
            await save_entity(storage, slug, "lessons", data)

        return {"promoted_to": "guideline", "guideline_id": guideline_id}

    elif target == "knowledge":
        async with _get_lock(slug, "lessons"):
            data = await load_entity(storage, slug, "lessons")
            lesson = find_item_or_404(data.get("lessons", []), lesson_id, "Lesson")

            if lesson.get("promoted_to_knowledge"):
                raise HTTPException(422, f"Already promoted to {lesson['promoted_to_knowledge']}")

        async with _get_lock(slug, "knowledge"):
            k_data = await load_entity(storage, slug, "knowledge")
            entries = k_data.get("knowledge", [])

            k_id = next_id(entries, "K")
            knowledge = {
                "id": k_id,
                "title": lesson["title"],
                "content": lesson["detail"],
                "category": body.category if body and body.category else "technical-context",
                "scopes": body.scopes if body and body.scopes else [],
                "tags": lesson.get("tags", []),
                "status": "ACTIVE",
                "promoted_from": lesson["id"],
                "versions": [],
                "linked_entities": [],
            }
            entries.append(knowledge)
            k_data["knowledge"] = entries
            await save_entity(storage, slug, "knowledge", k_data)

        async with _get_lock(slug, "lessons"):
            data = await load_entity(storage, slug, "lessons")
            lesson = find_item_or_404(data.get("lessons", []), lesson_id, "Lesson")
            lesson["promoted_to_knowledge"] = k_id
            await save_entity(storage, slug, "lessons", data)

        return {"promoted_to": "knowledge", "knowledge_id": k_id}

    raise HTTPException(422, f"Invalid target '{target}', use 'guideline' or 'knowledge'")
