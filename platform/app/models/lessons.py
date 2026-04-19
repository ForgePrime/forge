"""Project lessons (J4) + org-level anti-patterns (J5).

Lessons = "what worked" / "what didn't" captured on ACHIEVED objectives or incidents.
Anti-patterns = named failure modes promoted from lessons, injected into future prompts.
"""
import datetime as dt

from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean, CheckConstraint, func, Integer
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectLesson(Base):
    __tablename__ = "project_lessons"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('worked', 'didnt_work', 'incident', 'insight')",
            name="valid_lesson_kind",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"),
                                                    index=True)
    objective_external_id: Mapped[str | None] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}", nullable=False)
    source: Mapped[str | None] = mapped_column(String(64))  # e.g. "user", "llm-extract", "forge-self"
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                     server_default=func.now())


class AntiPattern(Base):
    """Org-level anti-pattern — injected into future LLM prompts to prevent repeat."""
    __tablename__ = "anti_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[str | None] = mapped_column(Text)          # concrete "don't do this" example
    correct_way: Mapped[str | None] = mapped_column(Text)      # concrete "do this instead"
    applies_to_kinds: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}",
                                                         nullable=False)  # e.g. ["test","import"]
    times_seen: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    promoted_from_lesson_id: Mapped[int | None] = mapped_column(ForeignKey("project_lessons.id"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    meta: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                     server_default=func.now())
