"""VerdictDivergence model — Phase A Stage A.3 shadow mode.

Per PLAN_GATE_ENGINE A.3:
    Shadow run: deploy with VERDICT_ENGINE_MODE=shadow. Run for >=1 week
    on real traffic. Divergences logged to verdict_divergences table.

Each row records a case where VerdictEngine (running in shadow mode)
disagreed with the legacy validator's verdict on the same artifact.
Phase A.4 cutover blocks until the table is reviewed by a distinct actor
and either:
- Zero divergences (cutover safe), OR
- Each divergence is explained + accepted in a written record.

Columns:
- execution_id: which Execution produced the divergence (FK).
- legacy_passed: bool — what the legacy validator returned.
- engine_passed: bool — what VerdictEngine.evaluate() returned.
- legacy_reason: text — for failed legacy verdicts, the failure reason.
- engine_reason: text — for failed engine verdicts, Verdict.reason.
- engine_rule_code: text — VerdictEngine's rule_code that triggered.
- artifact_summary: jsonb — small dict for triage (NOT the full artifact;
  artifact is reconstructable from the Execution).

Acyclicity / time semantics: created_at via TimestampMixin. Rows are
append-only; never UPDATEd.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class VerdictDivergence(Base, TimestampMixin):
    """A logged disagreement between VerdictEngine and legacy validator."""

    __tablename__ = "verdict_divergences"
    __table_args__ = (
        Index("ix_verdict_divergences_execution_id", "execution_id"),
        Index("ix_verdict_divergences_engine_rule_code", "engine_rule_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    legacy_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    engine_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    legacy_reason: Mapped[str | None] = mapped_column(Text)
    engine_reason: Mapped[str | None] = mapped_column(Text)
    engine_rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_summary: Mapped[dict | None] = mapped_column(JSONB)
