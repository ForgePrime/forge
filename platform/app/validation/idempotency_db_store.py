"""DBIdempotencyStore — Phase A Stage A.5 production backend.

Concrete implementation of IdempotencyStore Protocol (from
app/validation/idempotency.py) backed by the `idempotent_calls`
Postgres table.

Pairs with InMemoryIdempotencyStore (test backend). Both satisfy the
Protocol; production uses this DB-backed store, tests use the in-memory.

Per FORMAL P1 (Idempotence): same (tool, idempotency_key, args_hash)
within TTL returns cached result; never re-executes the underlying tool.

Determinism boundary: the store itself is deterministic given a
deterministic clock. The DB session is the only impure boundary.
Production callers acquire `session_factory` from
`app.database.get_db` or `SessionLocal()`.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.models.idempotent_call import IdempotentCall
from app.validation.idempotency import CacheHit, CacheLookup, CacheMiss


class DBIdempotencyStore:
    """SQLAlchemy-backed IdempotencyStore.

    Constructor takes a session factory (callable returning a Session)
    so the store doesn't hold a long-lived session — each get/put
    acquires a fresh session and closes it. This matches FastAPI's
    request-scoped session pattern.
    """

    def __init__(self, session_factory):
        """session_factory: callable returning a SQLAlchemy Session."""
        self._session_factory = session_factory

    def get(
        self,
        tool: str,
        idempotency_key: str,
        args_hash: str,
        now_ts: float,
    ) -> CacheLookup:
        """Look up a cached entry; respect TTL via expires_at column.

        Returns CacheHit if (tool, idempotency_key, args_hash) row exists
        AND row.expires_at > now (epoch-seconds comparison). Else
        CacheMiss with reason='not_found' or 'expired'.
        """
        session: Session = self._session_factory()
        try:
            row = (
                session.query(IdempotentCall)
                .filter(
                    IdempotentCall.tool == tool,
                    IdempotentCall.idempotency_key == idempotency_key,
                    IdempotentCall.args_hash == args_hash,
                )
                .first()
            )
            if row is None:
                return CacheMiss(reason="not_found")
            # row.expires_at is timezone-aware datetime; convert to epoch-seconds
            row_expires_ts = row.expires_at.timestamp()
            if row_expires_ts <= now_ts:
                return CacheMiss(reason="expired")
            return CacheHit(
                result=row.result_ref or {},
                cached_expires_at=row_expires_ts,
            )
        finally:
            session.close()

    def put(
        self,
        tool: str,
        idempotency_key: str,
        args_hash: str,
        result: dict,
        expires_at: float,
    ) -> None:
        """Insert or update the cache entry.

        Behavior:
        - If a row with the unique tuple already exists (e.g. expired),
          UPDATE its result_ref + expires_at.
        - Otherwise INSERT a new row.

        The unique constraint on (tool, idempotency_key, args_hash)
        guarantees at most one row per tuple.

        Per CONTRACT §A.6 disclosure: this is the only point where the
        store mutates DB state. Failures (connection loss, constraint
        violation under race) propagate to the caller — wrapping
        check_or_run in try/except is the caller's responsibility (or
        wrapping at FastAPI middleware level).
        """
        expires_dt = dt.datetime.fromtimestamp(expires_at, tz=dt.timezone.utc)
        session: Session = self._session_factory()
        try:
            existing = (
                session.query(IdempotentCall)
                .filter(
                    IdempotentCall.tool == tool,
                    IdempotentCall.idempotency_key == idempotency_key,
                    IdempotentCall.args_hash == args_hash,
                )
                .first()
            )
            if existing is not None:
                existing.result_ref = result
                existing.expires_at = expires_dt
            else:
                row = IdempotentCall(
                    tool=tool,
                    idempotency_key=idempotency_key,
                    args_hash=args_hash,
                    result_ref=result,
                    expires_at=expires_dt,
                )
                session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
