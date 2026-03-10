"""Knowledge router — CRUD + versions + impact + link/unlink."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/knowledge", tags=["knowledge"])


@router.get("")
async def list_knowledge(slug: str):
    return []


@router.post("", status_code=201)
async def create_knowledge(slug: str):
    return {}


@router.get("/{k_id}")
async def get_knowledge(slug: str, k_id: str):
    """Get knowledge — latest version."""
    return {}


@router.patch("/{k_id}")
async def update_knowledge(slug: str, k_id: str):
    """Update knowledge — creates new version."""
    return {}


@router.get("/{k_id}/versions")
async def list_versions(slug: str, k_id: str):
    return []


@router.get("/{k_id}/versions/{version}")
async def get_version(slug: str, k_id: str, version: int):
    return {}


@router.get("/{k_id}/impact")
async def impact_analysis(slug: str, k_id: str):
    """Impact analysis — entities affected by this knowledge."""
    return {}


@router.post("/{k_id}/link", status_code=201)
async def link_entity(slug: str, k_id: str):
    return {}


@router.delete("/{k_id}/link/{link_id}")
async def unlink_entity(slug: str, k_id: str, link_id: int):
    return {}
