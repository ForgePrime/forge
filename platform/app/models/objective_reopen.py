"""Objective re-open audit (D2) — preserves history when user pushes ACHIEVED back to ACTIVE."""
import datetime as dt

from sqlalchemy import Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ObjectiveReopen(Base):
    __tablename__ = "objective_reopens"

    id: Mapped[int] = mapped_column(primary_key=True)
    objective_id: Mapped[int] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    gap_notes: Mapped[str] = mapped_column(Text, nullable=False)
    prior_state: Mapped[dict] = mapped_column(JSONB, nullable=False)  # snapshot at re-open time
