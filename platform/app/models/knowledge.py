import datetime as dt

from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint, Table, Column, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

task_knowledge = Table(
    "task_knowledge",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("knowledge_id", Integer, ForeignKey("knowledge.id"), primary_key=True),
)


class Knowledge(Base, TimestampMixin):
    __tablename__ = "knowledge"
    __table_args__ = (
        CheckConstraint(
            "category IN ('requirement','domain-rules','api-reference','architecture',"
            "'business-context','technical-context','code-patterns','integration',"
            "'infrastructure','source-document','feature-spec')",
            name="valid_knowledge_category",
        ),
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','REVIEW_NEEDED','DEPRECATED','ARCHIVED')",
            name="valid_knowledge_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}", nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(30))
    source_ref: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False, server_default="system")
    # C1 — user-written context that helps Claude know what to focus on / ignore
    description: Mapped[str | None] = mapped_column(Text)
    focus_hint: Mapped[str | None] = mapped_column(Text)
    # C1 — for source_type='url': original URL; for 'folder': absolute path
    target_url: Mapped[str | None] = mapped_column(Text)
    # P3.5 — last time this source was injected into a Claude prompt (helps prune stale entries)
    last_read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
