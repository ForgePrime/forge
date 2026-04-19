import datetime as dt

from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrchestrateRun(Base):
    """Background orchestrate run — async lifecycle.

    Updated by background task at each step (claim, execute, verify, extract, challenge, done).
    UI polls this row every 2s to render live progress.
    """
    __tablename__ = "orchestrate_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','RUNNING','PAUSED','DONE','FAILED','CANCELLED','BUDGET_EXCEEDED','PARTIAL_FAIL','INTERRUPTED')",
            name="valid_orchestrate_run_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    started_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="PENDING")
    # P5.7 — bumped on every _update_run so orphan-recovery can detect stale workers.
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)  # max_tasks, enable_redis, etc.
    # Mockup 04 — pause request flag (cooperative, executor checks between tasks)
    pause_requested: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    paused_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    resumed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    # Live progress
    current_task_external_id: Mapped[str | None] = mapped_column(String(20))
    current_phase: Mapped[str | None] = mapped_column(String(32))  # claim|execute|verify|extract|challenge|done
    progress_message: Mapped[str | None] = mapped_column(Text)  # latest human-readable line

    # Counters
    tasks_completed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tasks_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")

    # Final
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    cancel_requested: Mapped[bool] = mapped_column(nullable=False, server_default="false")
