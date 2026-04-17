import datetime as dt

from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TestRun(Base):
    """Forge-executed test run — one row per pytest/jest invocation.

    Captures:
    - language detected
    - command executed
    - aggregate counts (collected/passed/failed/error/skipped)
    - per-AC verification mapping (which AC mapped to which tests, pass/fail)
    - stdout/stderr tails for debugging
    """
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("executions.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))

    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default="unknown")
    workspace_dir: Mapped[str] = mapped_column(Text, nullable=False)
    test_paths: Mapped[list[str] | None] = mapped_column(JSONB)  # filters passed to runner

    return_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    tests_collected: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tests_passed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tests_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tests_error: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tests_skipped: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    all_pass: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    results: Mapped[list[dict] | None] = mapped_column(JSONB)  # full per-test outcomes
    ac_mapping: Mapped[list[dict] | None] = mapped_column(JSONB)  # AC → test results
    summary_text: Mapped[str | None] = mapped_column(Text)
    stderr_tail: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
