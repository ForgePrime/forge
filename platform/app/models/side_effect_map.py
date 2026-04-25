"""SideEffectMap — persisted side-effects per Decision (Phase 1 redesign).

Persistence layer for the previously in-memory C.2 SideEffectRegistry.
Each row links a Decision to a side-effect kind, optional owner (NULL =
K1 owner-required gate WILL fire), optional evidence, blocking flag,
and JSONB impact_deltas validated by ADR-028 D3 discriminated union.

The SQL migration (§4 of 2026_04_26_phase1_redesign.sql) created the
underlying table; this model maps onto it.
"""

from __future__ import annotations

import datetime as dt
from sqlalchemy import BigInteger, Integer, String, Boolean, ForeignKey, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func as sqlfunc

from app.database import Base


class SideEffectMap(Base):
    """One side-effect entry on a Decision.

    K1 (owner-required) fires when `owner IS NULL` at execute time.
    `impact_deltas` JSONB validated by Pydantic at write boundary.
    """

    __tablename__ = "side_effect_map"
    __table_args__ = (
        CheckConstraint("length(kind) >= 1", name="sem_kind_nonempty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(128))
    evidence_set_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("evidence_sets.id", ondelete="SET NULL")
    )
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    impact_deltas: Mapped[list | None] = mapped_column(JSONB)
    # Created-at only (no updated_at column on this table per migration §4).
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=sqlfunc.now(), nullable=False
    )

    decision = relationship("Decision", foreign_keys=[decision_id])
    evidence_set = relationship("EvidenceSet", foreign_keys=[evidence_set_id])
