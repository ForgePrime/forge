"""HookRun — P1.2 audit row proving a ProjectHook actually fired.

Each row is one hook firing event: created when the executor reaches a DONE
task whose type matches a configured hook stage. Lets the UI show "last fired"
so the user can see the hook is alive, not silently ignored."""
import datetime as dt

from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HookRun(Base):
    __tablename__ = "hook_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('fired','skipped_no_skill','skipped_no_cli','error')",
            name="valid_hook_run_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    hook_id: Mapped[int] = mapped_column(
        ForeignKey("project_hooks.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"))
    llm_call_id: Mapped[int | None] = mapped_column(ForeignKey("llm_calls.id", ondelete="SET NULL"))

    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)  # preview of LLM output / skip reason
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
