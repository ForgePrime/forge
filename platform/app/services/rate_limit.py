"""Rate limiting — sliding-window counter on Redis.

Zero new dependencies — `redis` lib is already in the venv (6.4.0+).

Not wired into middleware by default (decision D-21, autonomous session):
a global 429 response would break integration tests that hammer the API.
Intended usage: opt-in per-endpoint via `check_rate_limit(...)` call at
the top of sensitive routes (e.g. /ingest, /orchestrate, /auth/login).

Usage:
    from app.services.rate_limit import check_rate_limit, RateLimitExceeded

    @router.post("/expensive")
    def expensive(request: Request):
        try:
            check_rate_limit(key=f"user:{current_user.id}",
                             max_per_window=60, window_sec=60)
        except RateLimitExceeded as e:
            raise HTTPException(429, {"retry_after": e.retry_after})
        ...

Limits are advisory guidance defaults — actual budgets should be tuned
per endpoint after measuring traffic. See `docs/SLO.md` for SLO context.

Architecture notes:
- Sliding window = current-second-window counter via INCR + EXPIRE.
  Cheap (2 Redis commands), approximate (may allow 2× peak briefly at
  window edge). For hard enforcement, consider leaky-bucket in Redis
  via a Lua script.
- If Redis is unavailable, policy falls OPEN (allows the call) and
  logs a warning. For strict mode, set `FORGE_RATE_LIMIT_FAIL_CLOSED=1`
  env (rejects when Redis is down). Default fail-open matches most
  production ops preferences (don't block prod on cache blip).
"""
from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when a key has exceeded its allowed rate.

    Attributes:
      retry_after: seconds until the window resets (int)
      limit:       the max_per_window that was exceeded (int)
      key:         the identifier that was rate-limited (str)
    """
    def __init__(self, retry_after: int, limit: int, key: str):
        self.retry_after = retry_after
        self.limit = limit
        self.key = key
        super().__init__(f"rate limit exceeded: {key} (limit={limit}/window, retry_after={retry_after}s)")


def _fail_closed() -> bool:
    return os.environ.get("FORGE_RATE_LIMIT_FAIL_CLOSED", "").lower() in ("1", "true", "yes")


def _get_redis():
    """Lazy redis client acquisition. Returns None when Redis is unavailable."""
    try:
        import redis
        from app.config import settings
        url = getattr(settings, "redis_url", None) or "redis://localhost:6379"
        return redis.Redis.from_url(url, decode_responses=True, socket_timeout=2)
    except Exception as e:  # pragma: no cover
        logger.warning("rate_limit: redis unavailable (%s)", e)
        return None


def check_rate_limit(
    key: str,
    max_per_window: int,
    window_sec: int = 60,
    *,
    redis_client=None,
    now: int | None = None,
) -> dict:
    """Check + increment a per-key counter. Raises RateLimitExceeded on breach.

    Args:
      key:            identifier (e.g. "user:42", "ip:1.2.3.4", "org:10:ingest")
      max_per_window: allowed calls per window
      window_sec:     window size in seconds (default 60)
      redis_client:   injected client for tests; default grabs from settings
      now:            injected unix timestamp for tests

    Returns:
      {"remaining": int, "reset_at": int_unix_ts, "limit": int}

    Raises:
      RateLimitExceeded: when the increment would push past `max_per_window`.
    """
    if max_per_window <= 0:
        # Zero-or-less limit = disabled; always pass.
        return {"remaining": -1, "reset_at": 0, "limit": max_per_window}

    client = redis_client if redis_client is not None else _get_redis()
    now = int(now if now is not None else time.time())
    window_id = now // window_sec
    reset_at = (window_id + 1) * window_sec

    if client is None:
        if _fail_closed():
            raise RateLimitExceeded(retry_after=window_sec, limit=max_per_window, key=key)
        # fail-open: allow + log
        logger.warning("rate_limit: redis unavailable, failing open for key=%s", key)
        return {"remaining": max_per_window - 1, "reset_at": reset_at, "limit": max_per_window}

    redis_key = f"rl:{key}:{window_id}"
    try:
        count = client.incr(redis_key)
        if count == 1:
            # First call in this window — set TTL so bucket auto-clears
            client.expire(redis_key, window_sec * 2)
    except Exception as e:
        if _fail_closed():
            raise RateLimitExceeded(retry_after=window_sec, limit=max_per_window, key=key)
        logger.warning("rate_limit: redis command failed (%s), failing open for key=%s", e, key)
        return {"remaining": max_per_window - 1, "reset_at": reset_at, "limit": max_per_window}

    count = int(count)
    if count > max_per_window:
        retry_after = max(1, reset_at - now)
        raise RateLimitExceeded(retry_after=retry_after, limit=max_per_window, key=key)

    return {
        "remaining": max(0, max_per_window - count),
        "reset_at": reset_at,
        "limit": max_per_window,
    }


def reset_key(key: str, *, redis_client=None) -> bool:
    """Admin helper — clear all windows for a key. Returns True if cleared."""
    client = redis_client if redis_client is not None else _get_redis()
    if client is None:
        return False
    try:
        keys = list(client.scan_iter(f"rl:{key}:*", count=100))
        if keys:
            client.delete(*keys)
        return True
    except Exception as e:  # pragma: no cover
        logger.warning("rate_limit: reset failed for %s: %s", key, e)
        return False
