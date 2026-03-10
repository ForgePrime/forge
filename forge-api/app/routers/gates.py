"""Gates router — show, configure, run checks."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/gates", tags=["gates"])


@router.get("")
async def show_gates(slug: str):
    return []


@router.post("", status_code=201)
async def configure_gates(slug: str):
    return {}


@router.post("/check")
async def run_gates(slug: str, task: str = ""):
    """Run all configured gates for a task."""
    return {}
