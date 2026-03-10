"""Decisions router — CRUD."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/decisions", tags=["decisions"])


@router.get("")
async def list_decisions(slug: str):
    return []


@router.post("", status_code=201)
async def add_decisions(slug: str):
    return {}


@router.get("/{decision_id}")
async def get_decision(slug: str, decision_id: str):
    return {}


@router.patch("/{decision_id}")
async def update_decision(slug: str, decision_id: str):
    return {}
