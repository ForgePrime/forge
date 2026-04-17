from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint("type IN ('bug', 'improvement', 'risk', 'dependency', 'question')", name="valid_finding_type"),
        CheckConstraint("severity IN ('HIGH', 'MEDIUM', 'LOW')", name="valid_finding_severity"),
        CheckConstraint(
            "status IN ('OPEN', 'APPROVED', 'DEFERRED', 'REJECTED')",
            name="valid_finding_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    line_number: Mapped[int | None] = mapped_column(Integer)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="OPEN")
    triage_reason: Mapped[str | None] = mapped_column(Text)
    triage_by: Mapped[str | None] = mapped_column(String(100))
    created_task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
