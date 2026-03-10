"""Tasks router — CRUD + next (claim) + complete + context assembly."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{slug}/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(slug: str):
    return []


@router.post("", status_code=201)
async def add_tasks(slug: str):
    return {}


@router.get("/{task_id}")
async def get_task(slug: str, task_id: str):
    return {}


@router.patch("/{task_id}")
async def update_task(slug: str, task_id: str):
    return {}


@router.delete("/{task_id}")
async def remove_task(slug: str, task_id: str):
    return {}


@router.post("/next")
async def claim_next_task(slug: str):
    """Claim the next available task (two-phase claim)."""
    return {}


@router.post("/{task_id}/complete")
async def complete_task(slug: str, task_id: str):
    return {}


@router.get("/{task_id}/context")
async def get_task_context(slug: str, task_id: str):
    """Assemble context for task execution."""
    return {}
