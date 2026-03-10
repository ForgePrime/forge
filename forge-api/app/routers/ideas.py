"""Ideas router — CRUD + hierarchy + commit."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/ideas", tags=["ideas"])


@router.get("")
async def list_ideas(slug: str):
    return []


@router.post("", status_code=201)
async def create_ideas(slug: str):
    return {}


@router.get("/{idea_id}")
async def get_idea(slug: str, idea_id: str):
    """Get idea detail — includes hierarchy and related decisions."""
    return {}


@router.patch("/{idea_id}")
async def update_idea(slug: str, idea_id: str):
    return {}


@router.post("/{idea_id}/commit")
async def commit_idea(slug: str, idea_id: str):
    """Commit idea — transition to COMMITTED status."""
    return {}
