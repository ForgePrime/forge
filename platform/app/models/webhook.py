import datetime as dt

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, CheckConstraint, Boolean, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Webhook(Base):
    """Outbound webhook configuration per organization."""
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    secret: Mapped[str] = mapped_column(String(64), nullable=False)  # HMAC signing
    events: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")  # ["task.done", "task.failed", "budget.exceeded"]
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_called_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[int | None] = mapped_column(Integer)
    last_error: Mapped[str | None] = mapped_column(Text)


class ShareLink(Base):
    """Capability-link tokens for sharing read-only views (e.g., task report).

    Token-in-URL pattern: anyone with link can view (no login).
    """
    __tablename__ = "share_links"
    __table_args__ = (
        CheckConstraint("scope IN ('task','project')", name="valid_share_scope"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_external_id: Mapped[str | None] = mapped_column(String(20))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
