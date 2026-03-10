"""Objectives router — CRUD + coverage dashboard."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/objectives", tags=["objectives"])


@router.get("")
async def list_objectives(slug: str):
    return []


@router.post("", status_code=201)
async def create_objectives(slug: str):
    return {}


@router.get("/status")
async def objectives_coverage(slug: str):
    """Coverage dashboard — KR progress, alignment."""
    return {}


@router.get("/{obj_id}")
async def get_objective(slug: str, obj_id: str):
    return {}


@router.patch("/{obj_id}")
async def update_objective(slug: str, obj_id: str):
    return {}
