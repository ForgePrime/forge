"""LLM Chat router — chat endpoint, provider management, config, sessions, file uploads."""

from __future__ import annotations

import io
import json
import logging
import os
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.dependencies import (
    get_llm_config,
    get_provider_registry,
    get_redis,
    get_session_manager,
    get_storage,
    get_tool_registry,
    get_event_bus,
)
from app.models.llm_config import LLMConfigUpdate

router = APIRouter(prefix="/llm", tags=["llm"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File upload constants
# ---------------------------------------------------------------------------

FILE_TTL_SECONDS = 60 * 60  # 1 hour
FILE_KEY_PREFIX = "chat:file:"
SESSION_FILES_KEY_PREFIX = "chat:session:"
SESSION_FILES_KEY_SUFFIX = ":files"

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
MAX_FILES_PER_SESSION = 10

ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".json",
    ".yaml", ".yml", ".sh", ".css", ".html", ".pdf",
}

CONTENT_PREVIEW_LENGTH = 500




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
    has_api_key: bool = False
    api_key_source: str = "none"  # "ui" | "env" | "config" | "none"


# Scope (frontend plural) → context_type (backend singular) mapping
SCOPE_TO_CONTEXT_TYPE: dict[str, str] = {
    "skills": "skill",
    "tasks": "task",
    "objectives": "objective",
    "ideas": "idea",
    "decisions": "decision",
    "knowledge": "knowledge",
    "guidelines": "guideline",
    "lessons": "lesson",
    "projects": "project",
    "ac_templates": "ac_template",
    "changes": "change",
    "research": "research",
    "dashboard": "global",
    "settings": "global",
}


class ChatRequest(BaseModel):
    """Request body for POST /llm/chat."""

    message: str = Field(..., min_length=1, max_length=10_000)
    context_type: str = Field(default="global", description="Entity context type")
    context_id: str = Field(default="", description="Entity ID (e.g., SK-001)")
    project: str = Field(default="", description="Project slug")
    session_id: str | None = Field(default=None, description="Resume existing session")
    model: str | None = Field(default=None, description="Override model")
    scopes: list[str] | None = Field(default=None, description="Frontend scopes (mapped to context_types)")
    disabled_capabilities: list[str] | None = Field(default=None, description="Tool names to disable")
    file_ids: list[str] | None = Field(default=None, description="Uploaded file IDs to include as context")
    page_context: str | None = Field(default=None, max_length=8000, description="Serialized UI page context from AI annotations")
    session_type: str | None = Field(default=None, description="Session type: chat, plan, execute, verify, compound")
    target_entity_type: str | None = Field(default=None, description="Entity type being worked on (objective, task, idea)")
    target_entity_id: str | None = Field(default=None, description="Target entity ID (e.g., O-001, T-003)")


class ChatResponse(BaseModel):
    """Response from POST /llm/chat."""

    session_id: str
    content: str
    model: str = ""
    iterations: int = 0
    tool_calls: list[dict[str, Any]] = []
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    stop_reason: str = ""


# ---------------------------------------------------------------------------
# Contract API — dynamic tool contracts from ToolRegistry
# ---------------------------------------------------------------------------


class PageRegisterRequest(BaseModel):
    """Request body for POST /llm/pages/register."""

    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    route: str = Field(default="", max_length=300)


@router.get("/contracts")
async def list_contracts(
    request: Request,
    scope: str | None = None,
    tool_registry=Depends(get_tool_registry),
):
    """List tool contracts, optionally filtered by scope (comma-separated)."""
    scopes = [s.strip() for s in scope.split(",") if s.strip()] if scope else None
    contracts = tool_registry.get_contracts(scopes)
    return {"contracts": contracts, "total": len(contracts)}


@router.get("/contracts/{tool_name}")
async def get_contract(
    tool_name: str,
    tool_registry=Depends(get_tool_registry),
):
    """Get a single tool's full contract."""
    contract = tool_registry.get_tool_contract(tool_name)
    if contract is None:
        raise HTTPException(404, f"Tool '{tool_name}' not found")
    return {"contract": contract}


# ---------------------------------------------------------------------------
# Page Registry — catalog of all Forge pages for App Context
# ---------------------------------------------------------------------------


@router.post("/pages/register")
async def register_page(body: PageRegisterRequest, request: Request):
    """Register a page (called by frontend on mount)."""
    registry = request.app.state.page_registry
    registry.register(body.id, body.title, body.description, body.route)
    return {"registered": True, "id": body.id}


@router.get("/pages")
async def list_pages(request: Request):
    """List all registered pages."""
    registry = request.app.state.page_registry
    pages = registry.get_all()
    return {"pages": pages, "count": len(pages)}


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    config=Depends(get_llm_config),
    registry=Depends(get_provider_registry),
    tool_registry=Depends(get_tool_registry),
    session_manager=Depends(get_session_manager),
    storage=Depends(get_storage),
    event_bus=Depends(get_event_bus),
    redis=Depends(get_redis),
) -> ChatResponse:
    """Send a message to LLM and get a response with tool-use support.

    Orchestrates: session → context → permissions → agent loop → save.
    Emits WS events for real-time streaming.
    """
    from core.llm.provider import CompletionConfig, Message, ProviderError
    from app.llm.agent_loop import AgentLoop, StreamEvent
    from app.llm.context_resolver import ContextResolver
    from app.llm.permissions import PermissionEngine

    # --- Check feature flag ---
    _CONTEXT_FLAG_MAP = {
        "skill": "skills", "task": "tasks", "objective": "objectives",
        "idea": "ideas", "knowledge": "knowledge", "guideline": "guidelines",
        "decision": "decisions", "lesson": "lessons", "project": "projects",
        "ac_template": "ac_templates", "change": "changes", "research": "research",
    }
    if body.context_type != "global":
        flag_name = _CONTEXT_FLAG_MAP.get(body.context_type)
        if flag_name:
            flags = config.feature_flags
            if hasattr(flags, flag_name) and not getattr(flags, flag_name, False):
                raise HTTPException(
                    status_code=403,
                    detail=f"LLM chat is disabled for module '{body.context_type}'. "
                           f"Enable it in Settings > LLM > Feature Flags.",
                )

    # --- Inject UI-stored API keys into registry ---
    if config.api_keys:
        registry.set_ui_keys(config.api_keys)

    # --- Resolve provider ---
    provider_name = config.default_provider
    try:
        provider = registry.get(provider_name)
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=f"LLM provider not available: {e}")

    caps = provider.capabilities()
    model = body.model or config.default_model or caps.model_id

    # --- Load or create session ---
    from app.llm.session_manager import ChatMessage

    session = None
    if body.session_id:
        session = await session_manager.load(body.session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{body.session_id}' not found or expired",
            )

    if session is None:
        session = await session_manager.create(
            context_type=body.context_type,
            context_id=body.context_id,
            project=body.project,
            model=model,
            session_type=body.session_type or "chat",
            target_entity_type=body.target_entity_type or "",
            target_entity_id=body.target_entity_id or "",
            scopes=body.scopes or [],
        )
    else:
        # Sync scopes if request scopes differ from session scopes
        # body.scopes=None means "not specified" (keep existing), body.scopes=[] means "clear"
        if body.scopes is not None and sorted(body.scopes) != sorted(session.scopes):
            await session_manager.update_scopes(session.session_id, body.scopes)
            session.scopes = body.scopes

    # --- Inject uploaded file content into user message ---
    user_content = body.message
    if body.file_ids and redis:
        file_parts: list[str] = []
        for fid in body.file_ids:
            file_key = f"{FILE_KEY_PREFIX}{fid}"
            raw = await redis.get(file_key)
            if raw is None:
                continue
            file_data = json.loads(raw)
            fname = file_data.get("filename", fid)
            content = file_data.get("content", "")
            file_parts.append(f"[Attached file: {fname}]\n{content}")
        if file_parts:
            user_content = "\n\n".join(file_parts) + "\n\n" + user_content

    # --- Add user message to session and build conversation ---
    session.messages.append(ChatMessage(role="user", content=user_content))
    await session_manager.save(session)

    messages: list[Message] = [
        Message(role=msg.role, content=msg.content)
        for msg in session.messages
    ]

    # --- Build system prompt (SKILL-like format) ---
    # 1. App Context — comprehensive SKILL (identity, modules, discovery, workflows)
    active_scopes = session.scopes  # Keep [] as-is (empty = no tools allowed)
    from app.llm.app_context_builder import AppContextBuilder
    builder = AppContextBuilder(
        tool_registry=tool_registry,
        page_registry=request.app.state.page_registry,
        custom_text=config.custom_app_context if hasattr(config, "custom_app_context") else "",
    )
    system_prompt = builder.build(
        active_scopes=active_scopes,
        project_slug=body.project or None,
    )

    # 2. Entity context (supplementary — what user is working on)
    resolver = ContextResolver(storage)
    context_payload = await resolver.resolve(
        context_type=body.context_type,
        context_id=body.context_id,
        project=body.project,
        scopes=session.scopes if session.scopes else body.scopes,
    )
    entity_context = context_payload.to_system_prompt()
    if entity_context:
        system_prompt += f"\n\n## Working Context\n\n{entity_context}"

    # 3. Page context from UI annotations (what user sees on screen)
    if body.page_context:
        system_prompt += f"\n\n{body.page_context}"

    # --- Build permissions ---
    permissions = PermissionEngine.load_permissions(config)

    # --- Build completion config ---
    completion_config = CompletionConfig(
        model=model,
        temperature=0.3,
        max_tokens=caps.max_output_tokens,
        system_prompt=system_prompt,
        metadata={"forge_session_id": session.session_id},
    )

    # --- Event callback (emit WS events) ---
    async def on_event(event: StreamEvent) -> None:
        if event_bus is None:
            return
        slug = body.project or "_global"
        event_type_map = {
            "token": "chat.token",
            "thinking": "chat.token",
            "tool_call": "chat.tool_call",
            "tool_result": "chat.tool_result",
            "complete": "chat.complete",
            "error": "chat.error",
        }
        ws_event = event_type_map.get(event.type)
        if ws_event:
            try:
                payload = {
                    "session_id": session.session_id,
                    **event.data,
                }
                # Add block_type discriminator for chat.token events
                # so frontend can distinguish thinking vs text content
                if ws_event == "chat.token":
                    payload["block_type"] = event.type  # "token" or "thinking"
                await event_bus.emit(slug, ws_event, payload)
            except Exception:
                logger.debug("Failed to emit WS event %s for session %s",
                             ws_event, session.session_id, exc_info=True)

    # --- Resolve context_types from scopes (if provided) ---
    context_types: str | list[str] = body.context_type
    if body.scopes:
        mapped = []
        for scope in body.scopes:
            ct = SCOPE_TO_CONTEXT_TYPE.get(scope, scope)
            if ct not in mapped:
                mapped.append(ct)
        context_types = mapped if mapped else body.context_type

    # --- Scope negotiation: tell LLM about inactive scopes ---
    unavailable = tool_registry.get_unavailable_scopes(
        context_type=context_types,
        permissions=permissions.permissions,
    )
    if unavailable:
        lines = [
            "## Scope Negotiation",
            "The following scopes are NOT currently active but can be enabled by the user:",
        ]
        for scope_name, tools in sorted(unavailable.items()):
            tool_list = ", ".join(tools[:5])
            if len(tools) > 5:
                tool_list += f", ... ({len(tools)} total)"
            lines.append(f"- **{scope_name}**: unlocks {tool_list}")
        lines.append(
            "\nIf the user asks about entities from an inactive scope, explain which "
            "scope is needed and include the marker [suggest-scope:SCOPENAME] in your "
            "response so the UI can show a clickable button to enable it."
        )
        system_prompt += "\n\n" + "\n".join(lines)

    # --- Run agent loop ---
    loop = AgentLoop(
        provider=provider,
        tool_registry=tool_registry,
        storage=storage,
        permissions=permissions.permissions,
        disabled_tools=body.disabled_capabilities,
        session_scopes=session.scopes,  # [] = enforce no scopes, None = no enforcement
        max_iterations=config.max_iterations_per_turn,
        max_total_tokens=config.max_tokens_per_session,
    )

    try:
        result = await loop.run(
            messages=messages,
            config=completion_config,
            context={
                "context_type": body.context_type,
                "context_types": context_types,
                "context_id": body.context_id,
                "entity_id": body.context_id,  # alias for skill tool handlers
                "project": body.project,
                "_tool_registry": tool_registry,
                "session_scopes": session.scopes,
            },
            on_event=on_event,
        )
    except Exception as e:
        # Save error message to keep conversation structure valid
        logger.exception("Agent loop failed for session %s", session.session_id)
        error_msg = f"[Error: {type(e).__name__}]"
        await session_manager.add_message(
            session_id=session.session_id,
            role="assistant",
            content=error_msg,
        )
        raise HTTPException(status_code=500, detail=f"Chat failed: {type(e).__name__}: {str(e)[:300]}")

    # --- Save assistant response to session ---
    tool_calls_data = [
        {"name": tc["name"], "input": tc["input"]}
        for tc in result.tool_calls_made
    ]

    await session_manager.add_message(
        session_id=session.session_id,
        role="assistant",
        content=result.content,
        tool_calls=tool_calls_data or None,
        tokens_used=result.total_output_tokens,
        is_input=False,
    )

    # Update session token counters
    await session_manager.update_tokens(
        session_id=session.session_id,
        input_tokens=result.total_input_tokens,
        output_tokens=result.total_output_tokens,
        cost_per_1k_input=caps.cost_per_1k_input,
        cost_per_1k_output=caps.cost_per_1k_output,
    )

    # --- Handle blocked_by_decision: pause the session ---
    if result.stop_reason == "blocked_by_decision" and result.blocked_by_decision_id:
        loaded = await session_manager.load(session.session_id)
        if loaded:
            loaded.session_status = "paused"
            loaded.pause_reason = "blocked_by_decision"
            loaded.blocked_by_decision_id = result.blocked_by_decision_id
            await session_manager.save(loaded)

        if event_bus:
            try:
                slug = body.project or "_global"
                await event_bus.emit(slug, "chat.paused", {
                    "session_id": session.session_id,
                    "reason": "blocked_by_decision",
                    "decision_id": result.blocked_by_decision_id,
                })
            except Exception:
                logger.debug("Failed to emit chat.paused event", exc_info=True)

    return ChatResponse(
        session_id=session.session_id,
        content=result.content,
        model=result.model,
        iterations=result.iterations,
        tool_calls=[
            {"name": tc["name"], "input": tc["input"], "result": tc.get("result")}
            for tc in result.tool_calls_made
        ],
        total_input_tokens=result.total_input_tokens,
        total_output_tokens=result.total_output_tokens,
        stop_reason=result.stop_reason,
    )


# ---------------------------------------------------------------------------
# Provider endpoints
# ---------------------------------------------------------------------------

@router.get("/providers")
async def list_providers(
    registry=Depends(get_provider_registry),
    config=Depends(get_llm_config),
) -> dict[str, Any]:
    """List all configured LLM providers."""
    ui_keys = config.api_keys or {}
    providers = []
    for name in registry.list_providers():
        pconfig = registry._configs.get(name, {})
        # Determine API key source
        has_key = False
        key_source = "none"
        if name in ui_keys and ui_keys[name]:
            has_key = True
            key_source = "ui"
        elif pconfig.get("api_key"):
            has_key = True
            key_source = "config"
        elif pconfig.get("api_key_env"):
            env_val = os.environ.get(pconfig["api_key_env"], "")
            if env_val:
                has_key = True
                key_source = "env"
        elif pconfig.get("provider", name) in ("ollama", "claude-code"):
            # Keyless providers — no API key needed
            has_key = True
            key_source = "login" if pconfig.get("provider", name) == "claude-code" else "none"
        providers.append(
            ProviderInfo(
                name=name,
                provider_type=pconfig.get("provider", name),
                default_model=pconfig.get("model", "unknown"),
                has_api_key=has_key,
                api_key_source=key_source,
            )
        )
    return {"providers": [p.model_dump() for p in providers]}


class ProviderModelInfo(BaseModel):
    id: str
    name: str
    context_window: int | None = None
    max_output: int | None = None
    supports_vision: bool = False


@router.get("/providers/{name}/models")
async def list_provider_models(
    name: str,
    registry=Depends(get_provider_registry),
    config=Depends(get_llm_config),
) -> dict[str, Any]:
    """List available models for a specific provider.

    Tries dynamic listing via API. Falls back to static model caps
    if provider can't be instantiated (e.g., no API key).
    """
    from core.llm.provider import ProviderError

    # Inject UI keys before accessing provider
    if config.api_keys:
        registry.set_ui_keys(config.api_keys)

    try:
        provider = registry.get(name)
        models = await provider.list_models()
        if models:
            return {"provider": name, "models": models}
    except (ProviderError, Exception) as e:
        logger.debug("Dynamic model list unavailable for %s: %s", name, e)

    # Fallback to static model caps
    pconfig = registry._configs.get(name, {})
    provider_type = pconfig.get("provider", name).lower()
    models = _static_model_list(provider_type)
    return {"provider": name, "models": models}


def _static_model_list(provider_type: str) -> list[dict[str, Any]]:
    """Return hardcoded model list for a provider type."""
    if provider_type == "anthropic":
        from core.llm.providers.anthropic import _MODEL_CAPS
        return [
            {"id": k, "name": k, "context_window": v["max_context_window"],
             "max_output": v["max_output_tokens"], "supports_vision": v.get("supports_vision", False)}
            for k, v in _MODEL_CAPS.items()
        ]
    elif provider_type == "openai":
        from core.llm.providers.openai import _MODEL_CAPS
        return [
            {"id": k, "name": k, "context_window": v["max_context_window"],
             "max_output": v["max_output_tokens"], "supports_vision": v.get("supports_vision", False)}
            for k, v in _MODEL_CAPS.items()
        ]
    elif provider_type == "claude-code":
        from core.llm.providers.claude_code import _MODEL_CAPS
        return [
            {"id": k, "name": k, "context_window": v["max_context_window"],
             "max_output": v["max_output_tokens"], "supports_vision": v.get("supports_vision", False)}
            for k, v in _MODEL_CAPS.items()
        ]
    return []


@router.post("/providers/test")
async def test_provider(
    body: ProviderTestRequest,
    registry=Depends(get_provider_registry),
    config=Depends(get_llm_config),
) -> ProviderTestResponse:
    """Test connection to an LLM provider with a simple completion call."""
    from core.llm.provider import (
        CompletionConfig,
        Message,
        ProviderError,
    )

    # Inject UI keys so test uses the user-configured key
    if config.api_keys:
        registry.set_ui_keys(config.api_keys)

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
        # Extract clean error message
        err_msg = str(e)
        # ProviderError wraps SDK errors — try to extract the inner message
        if "'message':" in err_msg:
            import re
            match = re.search(r"'message':\s*'([^']+)'", err_msg)
            if match:
                err_msg = match.group(1)
        return ProviderTestResponse(
            provider=body.provider,
            status="error",
            error=err_msg or f"Connection failed: {type(e).__name__}",
        )


@router.get("/config")
async def get_config(
    config=Depends(get_llm_config),
) -> dict[str, Any]:
    """Get current LLM configuration (feature flags, permissions, defaults)."""
    data = config.model_dump()
    # Mask API keys — show only last 4 chars
    if data.get("api_keys"):
        data["api_keys"] = {
            k: f"...{v[-4:]}" if len(v) > 4 else "****"
            for k, v in data["api_keys"].items()
        }
    return data


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
            elif key == "api_keys" and isinstance(value, dict):
                # Merge: empty string removes the key
                existing_keys = current.get("api_keys", {})
                for provider, api_key in value.items():
                    if api_key:
                        existing_keys[provider] = api_key
                    else:
                        existing_keys.pop(provider, None)
                current["api_keys"] = existing_keys
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

    # Mask API keys in response
    data = updated.model_dump()
    if data.get("api_keys"):
        data["api_keys"] = {
            k: f"...{v[-4:]}" if len(v) > 4 else "****"
            for k, v in data["api_keys"].items()
        }
    return data


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


@router.get("/sessions/search")
async def search_sessions(
    q: str = "",
    limit: int = 50,
    manager=Depends(get_session_manager),
) -> dict[str, Any]:
    """Search sessions by query string across message content.

    Returns matching sessions with a context snippet showing where the
    match was found. Empty query returns all sessions (same as list).
    """
    results = await manager.search_sessions(query=q, limit=limit)
    return {"sessions": results, "count": len(results), "query": q}


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


class UpdateScopesRequest(BaseModel):
    """Request body for PATCH /llm/sessions/{session_id}/scopes."""

    scopes: list[str] = Field(..., description="New list of allowed scopes for this session")


@router.patch("/sessions/{session_id}/scopes")
async def update_session_scopes(
    session_id: str,
    body: UpdateScopesRequest,
    manager=Depends(get_session_manager),
) -> dict[str, Any]:
    """Update allowed scopes for a session.

    Called by the frontend when the user toggles scopes in the Scopes tab.
    The new scopes take effect on the next agent loop iteration.
    """
    updated = await manager.update_scopes(session_id, body.scopes)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")

    session = await manager.load(session_id)
    return {
        "session_id": session_id,
        "scopes": session.scopes if session else body.scopes,
        "updated_at": session.updated_at if session else "",
    }


@router.post("/sessions/{session_id}/resume")
async def resume_session(
    session_id: str,
    manager=Depends(get_session_manager),
    event_bus=Depends(get_event_bus),
) -> dict[str, Any]:
    """Resume a paused session (e.g., after a blocking decision is resolved).

    Clears the pause_reason and blocked_by_decision_id fields,
    sets session_status back to 'active', and emits chat.resumed event.
    """
    session = await manager.load(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if session.session_status != "paused":
        return {"resumed": False, "session_id": session_id, "reason": "not_paused"}

    session.session_status = "active"
    decision_id = session.blocked_by_decision_id
    session.pause_reason = ""
    session.blocked_by_decision_id = ""
    await manager.save(session)

    if event_bus:
        slug = session.project or "_global"
        try:
            await event_bus.emit(slug, "chat.resumed", {
                "session_id": session_id,
                "decision_id": decision_id,
            })
        except Exception:
            logger.debug("Failed to emit chat.resumed event", exc_info=True)

    return {"resumed": True, "session_id": session_id}


# ---------------------------------------------------------------------------
# File upload endpoints — upload files for LLM context injection
# ---------------------------------------------------------------------------

class FileUploadResponse(BaseModel):
    """Response from POST /llm/chat/files."""

    file_id: str
    filename: str
    size: int
    content_type: str
    content_preview: str


@router.post("/chat/files", status_code=201)
async def upload_chat_file(
    file: UploadFile,
    session_id: str = Form(...),
    redis=Depends(get_redis),
) -> FileUploadResponse:
    """Upload a file for LLM context injection.

    The file is stored in Redis with a 1h TTL. The session_id is used
    as a grouping key for per-session file limits (max 10).
    Files can be uploaded before a chat session is formally created.

    Allowed extensions: .md, .txt, .py, .js, .ts, .json, .yaml, .yml,
    .sh, .css, .html, .pdf
    """

    # --- Validate file extension ---
    filename = file.filename or "unnamed"
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"File type '{ext}' not allowed. "
                f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # --- Read file with size limit (chunk-based to avoid buffering huge files) ---
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)  # 64KB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (>{MAX_FILE_SIZE} bytes). Maximum: 1MB",
            )
        chunks.append(chunk)
    content_bytes = b"".join(chunks)

    # --- Atomic session file limit (optimistic SADD + rollback) ---
    session_files_key = f"{SESSION_FILES_KEY_PREFIX}{session_id}{SESSION_FILES_KEY_SUFFIX}"
    temp_file_id = str(uuid.uuid4())
    await redis.sadd(session_files_key, temp_file_id)
    current_count = await redis.scard(session_files_key)
    if current_count > MAX_FILES_PER_SESSION:
        await redis.srem(session_files_key, temp_file_id)
        raise HTTPException(
            status_code=422,
            detail=f"Maximum {MAX_FILES_PER_SESSION} files per session reached",
        )

    # --- Extract text content ---
    content_text = ""
    if ext == ".pdf":
        content_text = _extract_pdf_text(content_bytes)
    else:
        try:
            content_text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content_text = content_bytes.decode("latin-1")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=422,
                    detail="File content could not be decoded as text",
                )

    # --- Store in Redis (reuse temp_file_id from the optimistic SADD) ---
    file_id = temp_file_id
    file_key = f"{FILE_KEY_PREFIX}{file_id}"

    file_data = {
        "file_id": file_id,
        "filename": filename,
        "size": len(content_bytes),
        "content_type": file.content_type or "application/octet-stream",
        "extension": ext,
        "session_id": session_id,
        "content": content_text,
    }

    # Store file data with 1h TTL
    await redis.setex(file_key, FILE_TTL_SECONDS, json.dumps(file_data))

    # Session set already has this file_id from optimistic SADD — refresh TTL
    await redis.expire(session_files_key, FILE_TTL_SECONDS)

    # Build content preview
    preview = content_text[:CONTENT_PREVIEW_LENGTH]
    if len(content_text) > CONTENT_PREVIEW_LENGTH:
        preview += "..."

    logger.info(
        "Uploaded file %s (%s, %d bytes) for session %s",
        file_id, filename, len(content_bytes), session_id,
    )

    return FileUploadResponse(
        file_id=file_id,
        filename=filename,
        size=len(content_bytes),
        content_type=file.content_type or "application/octet-stream",
        content_preview=preview,
    )


@router.get("/chat/files")
async def list_session_files(
    session_id: str,
    redis=Depends(get_redis),
) -> dict[str, Any]:
    """List all files uploaded for a given session.

    Returns file metadata (without full content) for each file.
    """
    session_files_key = f"{SESSION_FILES_KEY_PREFIX}{session_id}{SESSION_FILES_KEY_SUFFIX}"
    file_ids = await redis.smembers(session_files_key)

    files = []
    expired_ids = []

    for fid in file_ids:
        file_key = f"{FILE_KEY_PREFIX}{fid}"
        raw = await redis.get(file_key)
        if raw is None:
            # File expired but still in set — mark for cleanup
            expired_ids.append(fid)
            continue
        file_data = json.loads(raw)
        preview = file_data.get("content", "")[:CONTENT_PREVIEW_LENGTH]
        if len(file_data.get("content", "")) > CONTENT_PREVIEW_LENGTH:
            preview += "..."
        files.append({
            "file_id": file_data["file_id"],
            "filename": file_data["filename"],
            "size": file_data["size"],
            "content_type": file_data["content_type"],
            "extension": file_data["extension"],
            "content_preview": preview,
        })

    # Clean up expired file IDs from the session set
    if expired_ids:
        await redis.srem(session_files_key, *expired_ids)

    return {"session_id": session_id, "files": files, "count": len(files)}


@router.get("/chat/files/{file_id}")
async def get_chat_file(
    file_id: str,
    redis=Depends(get_redis),
) -> dict[str, Any]:
    """Retrieve a stored file's content by file_id.

    Returns the file metadata and full text content.
    File must not have expired (1h TTL).
    """
    file_key = f"{FILE_KEY_PREFIX}{file_id}"
    raw = await redis.get(file_key)

    if raw is None:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_id}' not found or expired",
        )

    file_data = json.loads(raw)
    return {
        "file_id": file_data["file_id"],
        "filename": file_data["filename"],
        "size": file_data["size"],
        "content_type": file_data["content_type"],
        "extension": file_data["extension"],
        "session_id": file_data["session_id"],
        "content": file_data["content"],
    }


@router.delete("/chat/files/{file_id}")
async def delete_chat_file(
    file_id: str,
    redis=Depends(get_redis),
) -> dict[str, Any]:
    """Delete a stored file by file_id.

    Also removes the file_id from the session's file set.
    """
    file_key = f"{FILE_KEY_PREFIX}{file_id}"
    raw = await redis.get(file_key)

    if raw is None:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_id}' not found or expired",
        )

    file_data = json.loads(raw)
    session_id = file_data.get("session_id", "")

    # Remove file data
    await redis.delete(file_key)

    # Remove from session file set
    if session_id:
        session_files_key = (
            f"{SESSION_FILES_KEY_PREFIX}{session_id}{SESSION_FILES_KEY_SUFFIX}"
        )
        await redis.srem(session_files_key, file_id)

    return {"deleted": True, "file_id": file_id}


# ---------------------------------------------------------------------------
# File content helpers for LLM context injection
# ---------------------------------------------------------------------------

async def get_session_file_contents(
    redis,
    session_id: str,
) -> list[dict[str, str]]:
    """Retrieve all file contents for a session — for LLM context injection.

    Returns a list of dicts with 'filename' and 'content' keys.
    This function is intended to be called from the chat endpoint or
    context resolver to inject uploaded file content into the LLM prompt.
    """
    session_files_key = f"{SESSION_FILES_KEY_PREFIX}{session_id}{SESSION_FILES_KEY_SUFFIX}"
    file_ids = await redis.smembers(session_files_key)

    results = []
    for fid in file_ids:
        file_key = f"{FILE_KEY_PREFIX}{fid}"
        raw = await redis.get(file_key)
        if raw is None:
            continue
        file_data = json.loads(raw)
        results.append({
            "file_id": file_data["file_id"],
            "filename": file_data["filename"],
            "content": file_data["content"],
        })

    return results


def _extract_pdf_text(content_bytes: bytes) -> str:
    """Attempt to extract text from PDF bytes.

    Uses PyPDF2/pypdf if available, otherwise returns a placeholder message.
    """
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(content_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        if pages:
            return "\n\n".join(pages)
        return "[PDF uploaded but no extractable text found]"
    except ImportError:
        pass
    except Exception as e:
        return f"[PDF text extraction failed: {type(e).__name__}]"

    try:
        import PyPDF2  # noqa: N813

        reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        if pages:
            return "\n\n".join(pages)
        return "[PDF uploaded but no extractable text found]"
    except ImportError:
        return "[PDF uploaded — text extraction unavailable (install pypdf)]"
    except Exception as e:
        return f"[PDF text extraction failed: {type(e).__name__}]"
