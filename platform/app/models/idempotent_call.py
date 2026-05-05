"""IdempotentCall model — Phase A Stage A.5 (MCP idempotency).

Per FORMAL_PROPERTIES_v2 P1 (Idempotence):
    T(T(x)) = T(x)  for stabilizing operations

Re-running the same intent on the same state with the same policy
produces the same result and no new write. Implemented at the MCP
boundary: every mutating tool call carries `idempotency_key`; within
TTL, a duplicate `(tool, idempotency_key, args_hash)` tuple returns
the original result without re-execution.

Schema choice notes:
- `result_ref` stores the cached response as JSONB. It is NOT a foreign
  key to another entity because the result type varies per tool
  (ExecutionId for forge_execute, Verdict for forge_deliver, etc.).
- `expires_at` is the wall-clock TTL boundary; rows past expiry are
  garbage-collectable but NOT auto-deleted (audit retention).
- Unique constraint covers `(tool, idempotency_key, args_hash)` —
  args_hash distinguishes the case where same key is reused with
  different arguments (e.g. retry that mutated a payload field).
- `args_hash` is sha256 hex (64 chars) of canonical-JSON-serialized
  args (sort_keys=True, no whitespace).

Migration: alembic version pending (separate commit — needs running
DB to verify upgrade/downgrade round-trip per A.5 T1).

Per CONTRACT §B.2 [ASSUMED]: ttl_default_seconds = 86400 (24 hours)
is an engineering-default starting value; ADR-004 supersession needs
to add `idempotency_ttl` to the calibration constants list. Tracked
in this commit's message as residual gap.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


# Default TTL: 24h. ADR-004 supersession should set this per-tool or
# globally. Used by app/validation/idempotency.py default arg.
DEFAULT_IDEMPOTENCY_TTL_SECONDS: int = 86400


class IdempotentCall(Base, TimestampMixin):
    """Cached result of a mutating MCP tool call within TTL.

    Lookup key: (tool, idempotency_key, args_hash). On match within
    expires_at > now(): return cached result. On miss: execute the tool
    and INSERT a row.

    args_hash distinguishes the "same key, different args" case (e.g.
    retry with payload field changed) from "same key, same args, dedup".
    """

    __tablename__ = "idempotent_calls"
    __table_args__ = (
        UniqueConstraint(
            "tool",
            "idempotency_key",
            "args_hash",
            name="uq_idempotent_calls_tool_key_args",
        ),
        Index("ix_idempotent_calls_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tool: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    args_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex
    result_ref: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
