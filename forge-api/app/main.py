"""Forge Platform v2 — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.auth import get_current_user
from app.contract_validation import ContractValidationMiddleware
from app.events import EventBus
from app.routers import (
    ac_templates,
    ai,
    auth,
    changes,
    contracts,
    debug,
    decisions,
    execution,
    gates,
    graph,
    guidelines,
    ideas,
    knowledge,
    lessons,
    llm_chat,
    maintenance,
    notifications,
    objectives,
    projects,
    research,
    skills,
    tasks,
    workflows,
    ws,
)


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — DB pool, Redis, storage adapter, LLM."""

    # --- Startup ---
    # Database pool — always created when DATABASE_URL is available.
    # Used by workflow engine (O-001) regardless of storage_mode,
    # and by entity storage when storage_mode == "postgresql".
    if settings.database_url:
        app.state.db_pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
        )
    else:
        app.state.db_pool = None

    # Redis client
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    # Storage adapter
    if settings.storage_mode == "json":
        from core.storage import JSONFileStorage
        app.state.storage = JSONFileStorage(settings.json_data_dir)
    else:
        # PostgreSQL adapter will be initialized when available
        app.state.storage = None

    # Event bus (Redis Pub/Sub)
    app.state.event_bus = EventBus(app.state.redis)

    # Debug capture service (LLM Debug Monitor)
    from app.debug_capture import DebugCapture
    app.state.debug_capture = DebugCapture(app.state.storage, app.state.event_bus)

    # LLM Provider Registry — load from providers.toml
    from pathlib import Path
    from core.llm.providers.registry import ProviderRegistry

    llm_config_path = Path(settings.llm_config_path)
    if llm_config_path.exists():
        app.state.provider_registry = ProviderRegistry.from_toml(llm_config_path)
    else:
        app.state.provider_registry = ProviderRegistry()

    # LLM Config — load from _global/llm_config.json or use defaults
    app.state.llm_config = _load_llm_config()

    # Notification Service (O-002) — event-to-notification mapping
    from app.services.notification_service import NotificationService
    app.state.notification_service = NotificationService(app.state.storage, app.state.event_bus)

    # LLM Tool Registry — built-in tools for LLM agents
    from app.llm.tool_registry import create_default_registry
    app.state.tool_registry = create_default_registry()

    # LLM Page Registry — catalog of all Forge pages for App Context
    from app.llm.page_registry import PageRegistry
    app.state.page_registry = PageRegistry()

    # LLM Session Manager — chat conversation persistence in Redis
    from app.llm.session_manager import SessionManager
    app.state.session_manager = SessionManager(app.state.redis, app.state.event_bus)

    # Workflow Engine (O-001) — only when DB pool is available
    if app.state.db_pool is not None:
        from app.workflow.store import WorkflowStore
        from app.workflow.engine import WorkflowEngine
        from app.workflow.models import StepType
        from app.workflow.steps import (
            ForgeCommandStepExecutor,
            UserDecisionStepExecutor,
        )

        app.state.workflow_store = WorkflowStore(app.state.db_pool)
        step_executors = {
            StepType.forge_command: ForgeCommandStepExecutor(),
            StepType.user_decision: UserDecisionStepExecutor(app.state.event_bus),
        }
        app.state.workflow_engine = WorkflowEngine(
            store=app.state.workflow_store,
            event_bus=app.state.event_bus,
            step_executors=step_executors,
        )
        # Register built-in workflow definitions (if available)
        try:
            from app.workflow.presets import BUILTIN_DEFINITIONS
            for defn in BUILTIN_DEFINITIONS.values():
                app.state.workflow_engine.register_definition(defn)
        except ImportError:
            pass  # Presets not yet created (T-067)
        # Recover stale executions from previous run
        recovered = await app.state.workflow_engine.recover()
        if recovered:
            import logging
            logging.getLogger(__name__).info("Recovered %d stale workflow(s)", recovered)
    else:
        app.state.workflow_store = None
        app.state.workflow_engine = None

    yield

    # --- Shutdown ---
    if app.state.db_pool is not None:
        await app.state.db_pool.close()
    await app.state.redis.aclose()


def _load_llm_config() -> "LLMConfig":
    """Load LLM config from _global/llm_config.json or return defaults."""
    import json
    import logging
    from pathlib import Path
    from app.models.llm_config import LLMConfig

    config_path = Path(settings.json_data_dir) / "_global" / "llm_config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return LLMConfig(**data)
        except Exception:
            logging.getLogger(__name__).warning(
                "Failed to load LLM config from %s, using defaults",
                config_path,
                exc_info=True,
            )
    return LLMConfig()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Forge Platform v2",
    version="2.0.0",
    description="Structured Change Orchestrator — REST API & WebSocket server",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Contract validation — validates request bodies against entity contracts.
# Runs before auth (defense-in-depth: reject malformed payloads early).
# Disable globally with FORGE_SKIP_CONTRACT_VALIDATION=true env var.
app.add_middleware(ContractValidationMiddleware)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

class ForgeValidationError(ValueError):
    """Raised for request validation errors — returns 422."""
    pass


class ForgeNotFoundError(KeyError):
    """Raised when an entity is not found — returns 404."""
    pass


@app.exception_handler(ForgeValidationError)
async def validation_error_handler(request: Request, exc: ForgeValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ForgeNotFoundError)
async def not_found_error_handler(request: Request, exc: ForgeNotFoundError):
    return JSONResponse(status_code=404, content={"detail": f"Not found: {exc}"})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/v1/health")
async def health_v1():
    return {"status": "ok", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

PREFIX = "/api/v1"

# Auth router — no auth required (login endpoint)
app.include_router(auth.router, prefix=PREFIX)

# Entity routers — protected by auth dependency
auth_deps = [Depends(get_current_user)]
app.include_router(projects.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(objectives.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(ideas.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(tasks.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(decisions.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(knowledge.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(maintenance.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(guidelines.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(changes.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(lessons.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(research.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(ac_templates.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(gates.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(graph.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(contracts.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(execution.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(debug.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(ai.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(llm_chat.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(notifications.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(notifications.global_router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(skills.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(workflows.router, prefix=PREFIX, dependencies=auth_deps)
app.include_router(ws.router)
app.include_router(execution.ws_router)  # Execution WS — own auth, no HTTP deps
app.include_router(workflows.ws_router)  # Workflow WS — own auth, no HTTP deps
