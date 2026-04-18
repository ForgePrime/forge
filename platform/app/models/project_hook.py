"""Post-stage hooks (H1) — fire specific skills after every task of a given stage completes."""
import datetime as dt

from sqlalchemy import String, Text, ForeignKey, CheckConstraint, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectHook(Base):
    __tablename__ = "project_hooks"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('after_analysis', 'after_planning', 'after_develop', 'after_documentation')",
            name="valid_hook_stage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"),
                                             index=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"))
    purpose_text: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                     server_default=func.now())
