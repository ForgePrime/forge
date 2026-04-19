import datetime as dt

from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint, Table, Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

task_dependencies = Table(
    "task_dependencies",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("depends_on_id", Integer, ForeignKey("tasks.id"), primary_key=True),
    CheckConstraint("task_id != depends_on_id", name="no_self_dep"),
)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "instruction IS NOT NULL OR description IS NOT NULL",
            name="task_has_content",
        ),
        CheckConstraint(
            # Original 4 types kept for backwards compat with existing rows.
            # New 4 (D1) describe the task's role in the per-objective lifecycle.
            "type IN ('feature', 'bug', 'chore', 'investigation', "
            "'analysis', 'planning', 'develop', 'documentation')",
            name="valid_task_type",
        ),
        CheckConstraint(
            "status IN ('TODO', 'CLAIMING', 'IN_PROGRESS', 'DONE', 'FAILED', 'SKIPPED')",
            name="valid_task_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instruction: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="feature")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="TODO")
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}", nullable=False)
    origin: Mapped[str | None] = mapped_column(String(20))
    produces: Mapped[dict | None] = mapped_column(JSONB)
    alignment: Mapped[dict | None] = mapped_column(JSONB)
    exclusions: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    ceremony_level: Mapped[str | None] = mapped_column(String(20))
    agent: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    started_at_commit: Mapped[str | None] = mapped_column(String(50))
    skip_reason: Mapped[str | None] = mapped_column(Text)
    fail_reason: Mapped[str | None] = mapped_column(Text)
    requirement_refs: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    completes_kr_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    # P2.1 — when this task was auto-created from a finding, track the link
    origin_finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id", ondelete="SET NULL"))
    # CGAID Artifact #4 Handoff — explicit risks per task
    # Shape: list[{risk: str, mitigation: str, severity: "LOW|MEDIUM|HIGH", owner: str|null}]
    risks: Mapped[list[dict] | None] = mapped_column(JSONB)

    project: Mapped["Project"] = relationship(back_populates="tasks")
    acceptance_criteria: Mapped[list["AcceptanceCriterion"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="AcceptanceCriterion.position"
    )
    executions: Mapped[list["Execution"]] = relationship(back_populates="task", order_by="Execution.id.desc()")
    dependencies = relationship(
        "Task",
        secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.task_id,
        secondaryjoin=id == task_dependencies.c.depends_on_id,
        backref="dependents",
    )


class AcceptanceCriterion(Base):
    __tablename__ = "acceptance_criteria"
    __table_args__ = (
        CheckConstraint("length(text) >= 20", name="ac_min_length"),
        CheckConstraint(
            "scenario_type IN ('positive', 'negative', 'edge_case', 'regression')",
            name="valid_scenario_type",
        ),
        CheckConstraint(
            "verification IN ('test', 'command', 'manual')",
            name="valid_verification",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="positive")
    verification: Mapped[str] = mapped_column(String(20), nullable=False, server_default="manual")
    test_path: Mapped[str | None] = mapped_column(String(300))
    command: Mapped[str | None] = mapped_column(Text)
    # B2 — source attribution: SRC-XXX or objective ref. NULL → "INVENTED BY LLM" badge.
    source_ref: Mapped[str | None] = mapped_column(Text)
    # B1 — last execution timestamp (for "manual unrun" trust-debt counter).
    last_executed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # B4 — reasoning trace: which LLM call produced this AC (NULL = user-added).
    source_llm_call_id: Mapped[int | None] = mapped_column(ForeignKey("llm_calls.id"))

    task: Mapped["Task"] = relationship(back_populates="acceptance_criteria")
