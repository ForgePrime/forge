"""KillCriteriaEventLog — append-only audit of K1..K6 firings (Phase 1).

K1 owner-required, K2 evidence-link, K3 reversibility, K4 solo-verifier,
K5 budget-cap, K6 contract-violation. These are gates over GateRegistry —
this table is a *firing audit*, not the gates themselves. Phase 1
migration §6 created the underlying table.

Powers DashboardView K1..K6 panel (last-24h tripped counts) once
instrumentation wires GateRegistry hooks to write rows here.
"""

from __future__ import annotations

import datetime as dt
from sqlalchemy import BigInteger, Integer, String, Text, ForeignKey, CheckConstraint, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func as sqlfunc

from app.database import Base


class KillCriteriaEventLog(Base):
    """One K1..K6 firing event. Append-only.

    At least one of (objective_id, decision_id, task_id) must be non-NULL
    so each row references a meaningful entity.
    """

    __tablename__ = "kill_criteria_event_log"
    __table_args__ = (
        CheckConstraint(
            "kc_code IN ('K1','K2','K3','K4','K5','K6')",
            name="kc_code_valid",
        ),
        CheckConstraint("length(reason) >= 5", name="kc_reason_nonempty"),
        CheckConstraint(
            "objective_id IS NOT NULL OR decision_id IS NOT NULL OR task_id IS NOT NULL",
            name="kc_at_least_one_ref",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    objective_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("objectives.id", ondelete="SET NULL")
    )
    decision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("decisions.id", ondelete="SET NULL")
    )
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="SET NULL")
    )
    kc_code: Mapped[str] = mapped_column(String(8), nullable=False)
    fired_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sqlfunc.now(),
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_set_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("evidence_sets.id", ondelete="SET NULL")
    )

    objective = relationship("Objective", foreign_keys=[objective_id])
    decision = relationship("Decision", foreign_keys=[decision_id])
    task = relationship("Task", foreign_keys=[task_id])
    evidence_set = relationship("EvidenceSet", foreign_keys=[evidence_set_id])
