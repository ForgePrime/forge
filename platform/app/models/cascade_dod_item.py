"""CascadeDodItem — Definition-of-Done checklist per Objective (Phase 1).

Replaces the legacy `objectives.success_criteria TEXT` blob with a typed
checklist. Each row is an ordered checkpoint with optional sign-off
metadata. Phase 1 migration §5 created the underlying table.
"""

from __future__ import annotations

import datetime as dt
from sqlalchemy import BigInteger, Integer, SmallInteger, String, Text, ForeignKey, CheckConstraint, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func as sqlfunc

from app.database import Base


class CascadeDodItem(Base):
    """One DoD checkpoint on an Objective.

    `signed_by` + `signed_at` are paired: both NULL or both NOT NULL
    (enforced by `dod_signature_complete` CHECK constraint).
    """

    __tablename__ = "cascade_dod_item"
    __table_args__ = (
        CheckConstraint("position >= 0", name="dod_position_nonneg"),
        CheckConstraint("length(text) >= 10", name="dod_text_nonempty"),
        UniqueConstraint("objective_id", "position", name="dod_uniq_pos_per_obj"),
        CheckConstraint(
            "(signed_by IS NULL AND signed_at IS NULL) OR "
            "(signed_by IS NOT NULL AND signed_at IS NOT NULL)",
            name="dod_signature_complete",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    objective_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    signed_by: Mapped[str | None] = mapped_column(String(128))
    signed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # Created-at only (no updated_at column on this table per migration §5).
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=sqlfunc.now(), nullable=False
    )

    objective = relationship("Objective", foreign_keys=[objective_id])
