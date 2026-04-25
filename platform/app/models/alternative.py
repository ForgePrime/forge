"""Alternative — CGAID alternatives per Decision (Phase 1 redesign).

Replaces the legacy `decisions.alternatives_considered TEXT` free-form
blob with a typed table. Each row carries position, text, optional source
citation, blocks count, optional task reference, JSONB impact_deltas
(validated by Pydantic discriminated union per ADR-028 D3), and optional
rejected_because (P21 root_cause_uniqueness alignment).

The SQL migration (§3 of platform/docs/migrations_drafts/2026_04_26_phase1_redesign.sql)
created the underlying table; this model maps onto it.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer, ForeignKey, SmallInteger, Text, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Alternative(Base, TimestampMixin):
    """One CGAID alternative considered for a Decision.

    Each Decision has 0..N alternatives (P21 require ≥2 for root_cause type).
    `impact_deltas` is JSONB validated at write boundary by
    app/schemas/side_effect_map.py::ImpactDelta discriminated union per
    ADR-028 D3.
    """

    __tablename__ = "alternatives"
    __table_args__ = (
        CheckConstraint("position >= 0", name="alt_position_nonneg"),
        CheckConstraint("length(text) >= 5", name="alt_text_nonempty"),
        UniqueConstraint("decision_id", "position", name="alt_uniq_pos_per_dec"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    src: Mapped[str | None] = mapped_column(Text)
    blocks_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    task_ref: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="SET NULL")
    )
    impact_deltas: Mapped[list | None] = mapped_column(JSONB)
    rejected_because: Mapped[str | None] = mapped_column(Text)

    # Optional ORM relationships (defined here for clarity; Decision side
    # adds `alternatives` backref in app/models/decision.py).
    decision = relationship("Decision", foreign_keys=[decision_id])
    task = relationship("Task", foreign_keys=[task_ref])
