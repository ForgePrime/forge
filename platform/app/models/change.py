from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Change(Base, TimestampMixin):
    __tablename__ = "changes"
    __table_args__ = (
        CheckConstraint("action IN ('create', 'edit', 'delete', 'rename', 'move')", name="valid_change_action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("executions.id"))
    external_id: Mapped[str] = mapped_column(String(20), nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    lines_added: Mapped[int] = mapped_column(Integer, server_default="0")
    lines_removed: Mapped[int] = mapped_column(Integer, server_default="0")
