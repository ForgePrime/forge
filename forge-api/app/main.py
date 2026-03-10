"""Forge Platform v2 — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import (
    ac_templates,
    changes,
    decisions,
    gates,
    guidelines,
    ideas,
    knowledge,
    lessons,
    objectives,
    projects,
    tasks,
)


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — DB pool, Redis, storage adapter."""

    # --- Startup ---
    # Database pool
    app.state.db_pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
    )

    # Redis client
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    # Storage adapter placeholder — will be set by PG or JSON adapter
    app.state.storage = None

    yield

    # --- Shutdown ---
    await app.state.db_pool.close()
    await app.state.redis.aclose()


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

app.include_router(projects.router, prefix=PREFIX)
app.include_router(objectives.router, prefix=PREFIX)
app.include_router(ideas.router, prefix=PREFIX)
app.include_router(tasks.router, prefix=PREFIX)
app.include_router(decisions.router, prefix=PREFIX)
app.include_router(knowledge.router, prefix=PREFIX)
app.include_router(guidelines.router, prefix=PREFIX)
app.include_router(changes.router, prefix=PREFIX)
app.include_router(lessons.router, prefix=PREFIX)
app.include_router(ac_templates.router, prefix=PREFIX)
app.include_router(gates.router, prefix=PREFIX)
