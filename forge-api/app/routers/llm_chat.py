"""LLM Chat router — provider management, config, and connection testing."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.dependencies import get_llm_config, get_provider_registry, get_session_manager
from app.models.llm_config import LLMConfigUpdate

router = APIRouter(prefix="/llm", tags=["llm"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ProviderTestRequest(BaseModel):
    provider: str = "anthropic"


class ProviderTestResponse(BaseModel):
    provider: str
    status: str  # "ok" | "error"
    model: str | None = None
    latency_ms: int | None = None
    message: str | None = None
    error: str | None = None


class ProviderInfo(BaseModel):
    name: str
    provider_type: str
    default_model: str
    status: str = "unchecked"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/providers")
async def list_providers(
    registry=Depends(get_provider_registry),
) -> dict[str, Any]:
    """List all configured LLM providers."""
    providers = []
    for name in registry.list_providers():
        config = registry._configs.get(name, {})
        providers.append(
            ProviderInfo(
                name=name,
                provider_type=config.get("provider", name),
                default_model=config.get("model", "unknown"),
            )
        )
    return {"providers": [p.model_dump() for p in providers]}


@router.post("/providers/test")
async def test_provider(
    body: ProviderTestRequest,
    registry=Depends(get_provider_registry),
) -> ProviderTestResponse:
    """Test connection to an LLM provider with a simple completion call."""
    from core.llm.provider import (
        CompletionConfig,
        Message,
        ProviderError,
    )

    try:
        provider = registry.get(body.provider)
    except ProviderError as e:
        return ProviderTestResponse(
            provider=body.provider,
            status="error",
            error=str(e),
        )

    try:
        caps = provider.capabilities()
        start = time.monotonic()
        result = await provider.complete(
            messages=[Message(role="user", content="Say 'hello' in one word.")],
            config=CompletionConfig(
                model=caps.model_id,
                max_tokens=16,
                temperature=0.0,
            ),
        )
        latency = int((time.monotonic() - start) * 1000)

        return ProviderTestResponse(
            provider=body.provider,
            status="ok",
            model=result.model,
            latency_ms=latency,
            message=result.content[:200],
        )
    except Exception as e:
        logger.exception("Provider test failed for %s", body.provider)
        return ProviderTestResponse(
            provider=body.provider,
            status="error",
            error=f"Connection failed: {type(e).__name__}",
        )


@router.get("/config")
async def get_config(
    config=Depends(get_llm_config),
) -> dict[str, Any]:
    """Get current LLM configuration (feature flags, permissions, defaults)."""
    return config.model_dump()


@router.put("/config")
async def update_config(
    request: Request,
    body: LLMConfigUpdate,
    config=Depends(get_llm_config),
) -> dict[str, Any]:
    """Update LLM configuration. Partial updates supported."""
    import json
    from pathlib import Path
    from app.config import settings as app_settings
    from app.models.llm_config import LLMConfig

    # Build updated config from current + partial update
    current = config.model_dump()

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            if key == "permissions" and isinstance(value, dict):
                # Deep merge: preserve unmentioned modules and fields
                for module, perms in value.items():
                    if module in current["permissions"]:
                        current["permissions"][module].update(
                            perms if isinstance(perms, dict) else perms.model_dump()
                        )
                    else:
                        current["permissions"][module] = (
                            perms if isinstance(perms, dict) else perms.model_dump()
                        )
            elif key == "feature_flags" and isinstance(value, dict):
                current["feature_flags"].update(
                    value if isinstance(value, dict) else value.model_dump()
                )
            else:
                current[key] = value

    updated = LLMConfig(**current)

    # Update in-memory config
    request.app.state.llm_config = updated

    # Persist to _global/llm_config.json
    config_dir = Path(app_settings.json_data_dir) / "_global"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "llm_config.json"
    config_path.write_text(
        json.dumps(updated.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return updated.model_dump()


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions(
    limit: int = 50,
    manager=Depends(get_session_manager),
) -> dict[str, Any]:
    """List active LLM chat sessions."""
    sessions = await manager.list_sessions(limit=limit)
    return {"sessions": sessions, "count": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    manager=Depends(get_session_manager),
) -> dict[str, Any]:
    """Get a chat session with full message history."""
    from fastapi import HTTPException

    session = await manager.load(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")
    return session.to_dict()


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    manager=Depends(get_session_manager),
) -> dict[str, Any]:
    """Delete a chat session."""
    from fastapi import HTTPException

    deleted = await manager.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"deleted": True, "session_id": session_id}
