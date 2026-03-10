"""FastAPI dependency injection — database, Redis, storage adapter."""

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
    return request.app.state.storage
