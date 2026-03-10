"""Lessons router — CRUD + promote."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/lessons", tags=["lessons"])


@router.get("")
async def list_lessons(slug: str):
    return []


@router.post("", status_code=201)
async def add_lessons(slug: str):
    return {}


@router.post("/{lesson_id}/promote")
async def promote_lesson(slug: str, lesson_id: str):
    """Promote lesson to guideline or knowledge."""
    return {}
