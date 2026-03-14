"""Workflow router — REST API + WebSocket for workflow execution management."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.workflow.events import ALL_WORKFLOW_EVENT_TYPES
from app.workflow.models import ExecutionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{slug}/workflows", tags=["workflows"])
ws_router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class WorkflowStartRequest(BaseModel):
    definition_id: str
    objective_id: str | None = None
    variables: dict[str, Any] | None = None


class WorkflowResumeRequest(BaseModel):
    user_response: Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_engine(request: Request):
    """Get WorkflowEngine from app state."""
    engine = getattr(request.app.state, "workflow_engine", None)
    if engine is None:
        raise HTTPException(503, "Workflow engine not initialized")
    return engine


def _get_store(request: Request):
    """Get WorkflowStore from app state."""
    store = getattr(request.app.state, "workflow_store", None)
    if store is None:
        raise HTTPException(503, "Workflow store not initialized")
    return store


async def _resolve_project_id(request: Request, slug: str) -> int:
    """Resolve project slug to internal DB id."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(503, "Database not available")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM projects WHERE slug = $1", slug
        )
        if not row:
            raise HTTPException(404, f"Project '{slug}' not found")
        return row["id"]


def _serialize_execution(execution) -> dict[str, Any]:
    """Serialize WorkflowExecution for JSON response."""
    data = execution.model_dump(mode="json")
    # Convert step_results dict values
    step_results = {}
    for sid, sr in execution.step_results.items():
        step_results[sid] = sr.model_dump(mode="json")
    data["step_results"] = step_results
    return data


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def start_workflow(slug: str, body: WorkflowStartRequest, request: Request):
    """Start a new workflow execution."""
    engine = _get_engine(request)
    project_id = await _resolve_project_id(request, slug)

    definition = engine.get_definition(body.definition_id)
    if not definition:
        raise HTTPException(404, f"Workflow definition '{body.definition_id}' not found")

    execution = await engine.start(
        definition=definition,
        project_slug=slug,
        project_id=project_id,
        objective_id=body.objective_id,
        variables=body.variables,
    )
    return _serialize_execution(execution)


@router.get("")
async def list_workflows(slug: str, request: Request, status: str | None = None):
    """List workflow executions for a project."""
    store = _get_store(request)
    project_id = await _resolve_project_id(request, slug)
    executions = await store.list_executions(project_id, status_filter=status)
    return {"workflows": [_serialize_execution(e) for e in executions]}


@router.get("/{ext_id}")
async def get_workflow(slug: str, ext_id: str, request: Request):
    """Get workflow execution details with step results."""
    store = _get_store(request)
    project_id = await _resolve_project_id(request, slug)
    execution = await store.get_execution_by_ext_id(project_id, ext_id)
    if not execution:
        raise HTTPException(404, f"Workflow '{ext_id}' not found")
    return _serialize_execution(execution)


@router.post("/{ext_id}/resume")
async def resume_workflow(
    slug: str, ext_id: str, body: WorkflowResumeRequest, request: Request,
):
    """Resume a paused workflow with user response."""
    engine = _get_engine(request)
    store = _get_store(request)
    project_id = await _resolve_project_id(request, slug)

    execution = await store.get_execution_by_ext_id(project_id, ext_id)
    if not execution:
        raise HTTPException(404, f"Workflow '{ext_id}' not found")

    if execution.status != ExecutionStatus.paused:
        raise HTTPException(
            409, f"Cannot resume: workflow is {execution.status.value}, expected paused"
        )

    resumed = await engine.resume(
        execution.id, body.user_response, slug, project_id,
    )
    return _serialize_execution(resumed)


@router.post("/{ext_id}/cancel")
async def cancel_workflow(slug: str, ext_id: str, request: Request):
    """Cancel a running or paused workflow."""
    engine = _get_engine(request)
    store = _get_store(request)
    project_id = await _resolve_project_id(request, slug)

    execution = await store.get_execution_by_ext_id(project_id, ext_id)
    if not execution:
        raise HTTPException(404, f"Workflow '{ext_id}' not found")

    if execution.status not in (
        ExecutionStatus.running, ExecutionStatus.paused, ExecutionStatus.pending,
    ):
        raise HTTPException(
            409, f"Cannot cancel: workflow is {execution.status.value}"
        )

    try:
        cancelled = await engine.cancel(execution.id, slug)
        return _serialize_execution(cancelled)
    except ValueError as e:
        raise HTTPException(409, str(e))


# ---------------------------------------------------------------------------
# WebSocket — workflow event streaming
# ---------------------------------------------------------------------------

_PING_INTERVAL = 30


@ws_router.websocket("/ws/projects/{slug}/workflows/{ext_id}")
async def workflow_events(websocket: WebSocket, slug: str, ext_id: str):
    """Stream real-time workflow events filtered by execution ext_id."""
    await websocket.accept()

    event_bus = websocket.app.state.event_bus
    pubsub = None
    try:
        pubsub = await event_bus.subscribe(slug)
        last_ping = time.monotonic()

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=0.05,
            )
            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    parsed = json.loads(data)
                    # Filter: only workflow events for this execution
                    event_type = parsed.get("event", "")
                    payload = parsed.get("payload", {})
                    if (
                        event_type in ALL_WORKFLOW_EVENT_TYPES
                        and payload.get("execution_id") == ext_id
                    ):
                        await websocket.send_text(data)
                except (json.JSONDecodeError, KeyError):
                    pass
            else:
                await asyncio.sleep(0.05)

            # Periodic ping
            if time.monotonic() - last_ping >= _PING_INTERVAL:
                await websocket.send_json({"event": "ping"})
                last_ping = time.monotonic()

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for workflow %s/%s", slug, ext_id)
    finally:
        if pubsub is not None:
            await pubsub.unsubscribe()
            if hasattr(pubsub, "aclose"):
                await pubsub.aclose()
            elif hasattr(pubsub, "close"):
                await pubsub.close()
