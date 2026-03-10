"""AC Templates router — CRUD + instantiate."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/ac-templates", tags=["ac-templates"])


@router.get("")
async def list_templates(slug: str):
    return []


@router.post("", status_code=201)
async def create_template(slug: str):
    return {}


@router.get("/{template_id}")
async def get_template(slug: str, template_id: str):
    return {}


@router.patch("/{template_id}")
async def update_template(slug: str, template_id: str):
    return {}


@router.post("/{template_id}/instantiate")
async def instantiate_template(slug: str, template_id: str):
    """Instantiate template with parameters."""
    return {}
