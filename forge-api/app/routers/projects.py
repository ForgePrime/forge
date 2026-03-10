"""Projects router — CRUD + status dashboard."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects():
    """List all projects."""
    return []


@router.post("", status_code=201)
async def create_project():
    """Create a new project."""
    return {}


@router.get("/{slug}")
async def get_project(slug: str):
    """Get project by slug."""
    return {}


@router.get("/{slug}/status")
async def project_status(slug: str):
    """Project dashboard — task counts, progress, blockers."""
    return {}
