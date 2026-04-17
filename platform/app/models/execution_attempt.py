import datetime as dt

from sqlalchemy import String, Text, Integer, ForeignKey, CheckConstraint, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExecutionAttempt(Base):
    """Records each delivery attempt for resubmit detection.

    One execution can have multiple attempts when contract validation REJECTS
    and agent retries. Used by contract_validator to detect loop patterns
    (same evidence resubmitted, or WARNINGs ignored across attempts).
    """
    __tablename__ = "execution_attempts"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('ACCEPTED','REJECTED','CHALLENGED')",
            name="valid_attempt_verdict",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reasoning_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_hash: Mapped[str | None] = mapped_column(String(64))
    submitted_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
