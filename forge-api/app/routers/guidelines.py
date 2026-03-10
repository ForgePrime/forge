"""Guidelines router — CRUD + context for LLM."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/guidelines", tags=["guidelines"])


@router.get("")
async def list_guidelines(slug: str):
    return []


@router.post("", status_code=201)
async def create_guidelines(slug: str):
    return {}


@router.patch("/{guideline_id}")
async def update_guideline(slug: str, guideline_id: str):
    return {}


@router.get("/context")
async def guidelines_context(slug: str, scopes: str = ""):
    """Get guidelines formatted for LLM context, filtered by scopes."""
    return {}
