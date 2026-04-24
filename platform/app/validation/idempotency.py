"""Idempotency middleware — Phase A Stage A.5.

Closes FORMAL_PROPERTIES_v2 P1 at the MCP boundary: every mutating tool
call's caller can supply an `idempotency_key`; within TTL, a duplicate
`(tool, idempotency_key, args_hash)` returns the cached result without
re-execution.

Layered design (testability):
- `IdempotencyStore` Protocol — the storage backend contract.
- `InMemoryIdempotencyStore` — pure-Python dict, no DB dep; used in tests
  and as a development scaffold.
- `DBIdempotencyStore` — backed by the `idempotent_calls` table (model
  in app/models/idempotent_call.py). Wired into mcp_server in a
  follow-up commit (requires alembic migration first).
- `check_or_run()` — the dispatch helper. Pure function over (store,
  clock, tool, key, args, factory). The factory callable is the only
  side-effecting input; if dispatch returns cached, factory is NOT
  invoked (idempotency invariant).

Determinism: `check_or_run()` is deterministic given a deterministic
`clock_fn` and a deterministic factory; tests inject a fake clock. The
production clock is `time.time` (wall-clock seconds since epoch).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class CacheHit:
    """Returned by IdempotencyStore.get when a cached result is fresh."""

    result: dict
    cached_expires_at: float  # epoch seconds; for diagnostics


@dataclass(frozen=True)
class CacheMiss:
    """Returned by IdempotencyStore.get when no fresh entry exists."""

    reason: str  # 'not_found' | 'expired'


CacheLookup = CacheHit | CacheMiss


class IdempotencyStore(Protocol):
    """Backend Protocol for caching idempotent call results.

    Implementations: InMemoryIdempotencyStore (in-process dict),
    DBIdempotencyStore (idempotent_calls table — separate file).
    """

    def get(
        self,
        tool: str,
        idempotency_key: str,
        args_hash: str,
        now_ts: float,
    ) -> CacheLookup:
        ...

    def put(
        self,
        tool: str,
        idempotency_key: str,
        args_hash: str,
        result: dict,
        expires_at: float,
    ) -> None:
        ...


class InMemoryIdempotencyStore:
    """In-process dict-backed store. Pure Python; safe for tests + small dev.

    Not thread-safe; intended for single-worker test scenarios. The DB
    store handles concurrency via the unique constraint.
    """

    def __init__(self) -> None:
        # key: (tool, idempotency_key, args_hash) -> (result, expires_at)
        self._cache: dict[tuple[str, str, str], tuple[dict, float]] = {}

    def get(
        self,
        tool: str,
        idempotency_key: str,
        args_hash: str,
        now_ts: float,
    ) -> CacheLookup:
        key = (tool, idempotency_key, args_hash)
        entry = self._cache.get(key)
        if entry is None:
            return CacheMiss(reason="not_found")
        result, expires_at = entry
        if expires_at <= now_ts:
            return CacheMiss(reason="expired")
        return CacheHit(result=result, cached_expires_at=expires_at)

    def put(
        self,
        tool: str,
        idempotency_key: str,
        args_hash: str,
        result: dict,
        expires_at: float,
    ) -> None:
        self._cache[(tool, idempotency_key, args_hash)] = (result, expires_at)

    def __len__(self) -> int:
        """Diagnostic: how many cached entries currently."""
        return len(self._cache)

    def __contains__(self, key: tuple[str, str, str]) -> bool:
        return key in self._cache


def canonical_args_hash(args: dict[str, Any]) -> str:
    """Deterministic SHA-256 of args.

    Canonical JSON: sort_keys=True, no whitespace, default str-coercion.
    Matches PostgreSQL JSONB sort-of-canonical form so DB-side hash and
    Python-side hash produce identical values for identical inputs.

    Important: types matter. `{"x": 1}` and `{"x": "1"}` produce different
    hashes (correct — different inputs).
    """
    serialized = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def check_or_run(
    store: IdempotencyStore,
    tool: str,
    idempotency_key: str,
    args: dict[str, Any],
    factory: Callable[[], dict],
    ttl_seconds: int,
    clock_fn: Callable[[], float] = time.time,
) -> dict:
    """Dispatch helper — return cached result if fresh, else run factory.

    Invariant: factory is invoked AT MOST ONCE per `(tool, idempotency_key,
    args_hash)` within the TTL window. Subsequent calls within TTL return
    the cached result without re-invoking factory.

    Behavior:
    - Cache hit (within TTL): return CacheHit.result; factory NOT called.
    - Cache miss (not_found): invoke factory; store result with expires_at;
      return result.
    - Cache miss (expired): invoke factory; OVERWRITE existing entry with
      new result + new expires_at; return new result. (TTL semantics —
      expired entries are stale, not authoritative.)

    Args:
        store: IdempotencyStore implementation (in-memory or DB).
        tool: MCP tool name (e.g. 'forge_execute').
        idempotency_key: caller-supplied key. Caller's responsibility to
            ensure uniqueness for distinct logical operations.
        args: tool arguments. SHA-256 canonical-JSON-hashed for the
            args_hash component of the cache key.
        factory: callable producing the fresh result on cache miss. MUST
            be a pure function of `args` for the idempotency invariant
            to hold (factory side-effects on miss are acceptable; on
            cache HIT they are skipped, which is the point).
        ttl_seconds: how long the result is cached. Default per
            DEFAULT_IDEMPOTENCY_TTL_SECONDS in app/models/idempotent_call.py
            (86400 = 24h, [ASSUMED] pending ADR-004 supersession).
        clock_fn: returns current epoch seconds. Default time.time;
            tests inject a fake.

    Returns:
        The result (cached or freshly produced).
    """
    args_hash = canonical_args_hash(args)
    now_ts = clock_fn()

    lookup = store.get(tool, idempotency_key, args_hash, now_ts)
    if isinstance(lookup, CacheHit):
        return lookup.result

    # Cache miss (not_found OR expired) — execute factory.
    result = factory()
    expires_at = now_ts + ttl_seconds
    store.put(tool, idempotency_key, args_hash, result, expires_at)
    return result
