"""Changes router — CRUD + auto-detect from git."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/changes", tags=["changes"])


@router.get("")
async def list_changes(slug: str):
    return []


@router.post("", status_code=201)
async def record_changes(slug: str):
    return {}


@router.post("/auto")
async def auto_detect_changes(slug: str):
    """Auto-detect changes from git diff."""
    return {}
