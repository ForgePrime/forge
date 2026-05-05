from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.epistemic import epistemic_tag_pg_enum, EpistemicTag


class Decision(Base, TimestampMixin):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'CLOSED', 'DEFERRED', 'ANALYZING', 'MITIGATED', 'ACCEPTED')",
            name="valid_decision_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("executions.id"))
    external_id: Mapped[str] = mapped_column(String(20), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="OPEN")
    severity: Mapped[str | None] = mapped_column(String(10))
    confidence: Mapped[str | None] = mapped_column(String(10))
    alternatives_considered: Mapped[dict | None] = mapped_column(JSONB)
    # Phase 1 redesign (ADR-028 D2 revised): epistemic basis of this Decision.
    # NULL = untagged legacy row.
    epistemic_tag: Mapped[EpistemicTag | None] = mapped_column(epistemic_tag_pg_enum)
    resolution_notes: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project"] = relationship(back_populates="decisions")
