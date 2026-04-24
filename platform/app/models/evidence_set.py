"""EvidenceSet model — Phase A Stage A.1 (shadow mode).

Per PLAN_GATE_ENGINE.md Stage A.1 and FORMAL_PROPERTIES_v2 P16/P17.
Entity required per Decision; enforces that every Decision write has
provenance-backed evidence (not assumption-based reasoning).

Shadow-mode: EvidenceSet rows are writable by application, but VerdictEngine
is not yet wired to enforce anything. Flag VERDICT_ENGINE_MODE=off by default
keeps blast radius at zero until Phase A.4 cutover.

Blocked on: ADR-004 CLOSED (for α-gate values in downstream stages) and
ADR-003 RATIFIED (for normative status transition).
"""

from sqlalchemy import String, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class EvidenceSet(Base, TimestampMixin):
    """Evidence backing a Decision claim.

    P16: every Decision must have ≥ 1 EvidenceSet row with non-empty provenance.
    P17 (partial): kind ∈ {test_output, command_output, api_response, log_output,
    metric, file_citation, code_reference, runtime_snapshot}; kind='assumption'
    rejected at DB constraint level.
    Full P17 enforcement adds application-level check in PLAN_CONTRACT_DISCIPLINE
    Stage F.1.
    """

    __tablename__ = "evidence_sets"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('test_output', 'command_output', 'api_response', "
            "'log_output', 'metric', 'file_citation', 'code_reference', "
            "'runtime_snapshot')",
            name="valid_evidence_kind",
        ),
        CheckConstraint(
            "provenance_url IS NOT NULL OR provenance_path IS NOT NULL",
            name="provenance_required",
        ),
        Index("ix_evidence_sets_decision_id", "decision_id"),
        Index("ix_evidence_sets_kind", "kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)

    # Provenance: at least one of URL or path must be populated (CHECK above).
    provenance_url: Mapped[str | None] = mapped_column(Text)
    provenance_path: Mapped[str | None] = mapped_column(Text)

    # For test_output / command_output — mandatory in Phase F.2 (P18):
    reproducer_ref: Mapped[str | None] = mapped_column(Text)

    # For file_citation / code_reference — mandatory in Phase F.2 (P18):
    checksum: Mapped[str | None] = mapped_column(String(64))  # sha256 hex

    # Sufficiency flag — per E.1 ContractSchema self-adjointness check:
    sufficient_for_json: Mapped[dict | None] = mapped_column(JSONB)

    # Free-form evidence content (structured by kind):
    content: Mapped[dict | None] = mapped_column(JSONB)

    decision: Mapped["Decision"] = relationship(backref="evidence_sets")
