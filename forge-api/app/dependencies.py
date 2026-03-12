"""FastAPI dependency injection — database, Redis, storage adapter, LLM."""

from __future__ import annotations

from typing import AsyncGenerator

import asyncpg
import redis.asyncio as aioredis
from fastapi import Depends, Request


# ---------------------------------------------------------------------------
# Database pool (asyncpg)
# ---------------------------------------------------------------------------

async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Return the app-wide connection pool (set during lifespan)."""
    return request.app.state.db_pool


async def get_db(pool: asyncpg.Pool = Depends(get_db_pool)) -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a single connection from the pool for one request."""
    async with pool.acquire() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

async def get_redis(request: Request) -> aioredis.Redis:
    """Return the app-wide Redis client (set during lifespan)."""
    return request.app.state.redis


# ---------------------------------------------------------------------------
# Storage adapter (abstract — implemented by PG adapter or JSON adapter)
# ---------------------------------------------------------------------------

async def get_storage(request: Request):
    """Return the storage adapter for the current storage mode.

    The actual adapter is created during app lifespan and stored on app.state.
    """
    storage = request.app.state.storage
    if storage is None:
        from fastapi import HTTPException
        raise HTTPException(503, "Storage adapter not configured")
    return storage


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

async def get_event_bus(request: Request):
    """Return the app-wide EventBus (set during lifespan)."""
    return getattr(request.app.state, "event_bus", None)


# ---------------------------------------------------------------------------
# LLM Provider Registry + Config
# ---------------------------------------------------------------------------

async def get_provider_registry(request: Request):
    """Return the app-wide ProviderRegistry (set during lifespan)."""
    return request.app.state.provider_registry


async def get_llm_config(request: Request):
    """Return the current LLM config."""
    return request.app.state.llm_config


async def get_llm_provider(request: Request):
    """Return the default LLM provider instance.

    Returns None if no provider is configured, API key is missing,
    or provider package is not installed.
    """
    registry = request.app.state.provider_registry
    config = request.app.state.llm_config
    try:
        return registry.get(config.default_provider)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# LLM Tool Registry
# ---------------------------------------------------------------------------

async def get_tool_registry(request: Request):
    """Return the app-wide ToolRegistry (set during lifespan)."""
    return request.app.state.tool_registry


# ---------------------------------------------------------------------------
# LLM Session Manager
# ---------------------------------------------------------------------------

async def get_session_manager(request: Request):
    """Return the app-wide SessionManager (set during lifespan)."""
    return request.app.state.session_manager


# ---------------------------------------------------------------------------
# Skill Storage + Git Sync
# ---------------------------------------------------------------------------

def get_skill_storage(request: Request):
    """Return the app-wide SkillStorageService.

    Lazily created and cached on app.state.
    """
    svc = getattr(request.app.state, "skill_storage", None)
    if svc is None:
        from pathlib import Path
        from app.services.skill_storage import SkillStorageService

        storage = request.app.state.storage
        # Derive skills_dir from storage base path if possible
        base = getattr(storage, "base_dir", None)
        if base:
            skills_dir = Path(base) / "_global" / "skills"
        else:
            skills_dir = Path("forge_output/_global/skills")
        svc = SkillStorageService(skills_dir)
        request.app.state.skill_storage = svc
    return svc


def _load_skills_config(request=None) -> dict:
    """Load persisted skills config from _global/skills_config.json."""
    import json
    from pathlib import Path

    # Try to get base_dir from storage
    base = None
    if request:
        storage = getattr(request.app.state, "storage", None)
        if storage:
            base = getattr(storage, "base_dir", None)

    if base:
        config_path = Path(base) / "_global" / "skills_config.json"
    else:
        config_path = Path("forge_output/_global/skills_config.json")

    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def get_git_sync(request: Request):
    """Return the app-wide GitSyncService (or None if not configured).

    Checks persisted config first, then env var.
    """
    svc = getattr(request.app.state, "git_sync", None)
    if svc is None:
        import os

        # Check persisted config, then env var
        config = _load_skills_config(request)
        url = config.get("repo_url", "") or os.environ.get("FORGE_SKILLS_REPO_URL", "")
        if not url:
            return None
        from app.services.git_sync import GitSyncService

        skill_storage = get_skill_storage(request)
        svc = GitSyncService(
            skills_dir=skill_storage.skills_dir,
            remote_url=url,
            skill_storage=skill_storage,
        )
        request.app.state.git_sync = svc
    return svc
