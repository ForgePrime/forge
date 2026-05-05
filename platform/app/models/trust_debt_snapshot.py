"""TrustDebtSnapshot — per-project trust-debt computation history (Phase 1).

Stores trust-debt index values + decomposition over time. The trust-debt
FORMULA is INVENTED in the redesign mock and requires Steward sign-off
before any value here is read in Steward-facing UI as authoritative.
Until then, dashboard renders it as "indicative only" (rendering layer
concern, not schema). Phase 1 migration §7 created the underlying table.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, Numeric, ForeignKey, CheckConstraint, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func as sqlfunc

from app.database import Base


class TrustDebtSnapshot(Base):
    """One trust-debt computation row.

    `value` is non-negative; `decomposition` JSONB carries per-component
    breakdown for explainability (typed shape via Pydantic at write
    boundary; not enforced at DB).
    """

    __tablename__ = "trust_debt_snapshot"
    __table_args__ = (
        CheckConstraint("value >= 0", name="td_value_nonneg"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sqlfunc.now(),
    )
    value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    decomposition: Mapped[dict | None] = mapped_column(JSONB)

    project = relationship("Project", foreign_keys=[project_id])
