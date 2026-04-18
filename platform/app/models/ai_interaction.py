"""AI sidebar interaction — immutable audit of every chat turn."""
import datetime as dt

from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)

    page_id: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(64))

    message: Mapped[str] = mapped_column(Text, nullable=False)
    plan_first: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Full request/response for audit + replay
    page_ctx: Mapped[dict] = mapped_column(JSONB, nullable=False)      # as received
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    tool_calls: Mapped[list | None] = mapped_column(JSONB)
    not_checked: Mapped[list | None] = mapped_column(JSONB)

    cost_usd: Mapped[float | None] = mapped_column(Float)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    model_used: Mapped[str | None] = mapped_column(String(64))

    # Errors (if any)
    error_kind: Mapped[str | None] = mapped_column(String(64))   # "timeout" | "claude_unavailable" | "invalid_ctx" | ...
    error_detail: Mapped[str | None] = mapped_column(Text)
