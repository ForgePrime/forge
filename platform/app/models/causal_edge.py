"""CausalEdge model — Phase B Stage B.1.

Per FORMAL_PROPERTIES_v2 P14 (Causal decision memory):
    History is a DAG G = (V, E) with V = {Decision, Change, Finding,
    AC, KR, Execution, EvidenceSet, LLMCall} and E carrying
    {justifies, supersedes, evidences, produced_by, blocks}.

This table replaces the implicit FK-only causal structure with an
explicit edge entity that captures relation type + temporal ordering.
Phase B.2 backfills existing FK-derived edges; Phase B.6 adds typed
relation_semantic ENUM atop the free-form relation TEXT.

Schema:
- (src_type, src_id) → (dst_type, dst_id) directed edge.
- relation TEXT — free-form at B.1 (e.g. 'depends_on', 'evidences',
  'supersedes'). Constrained ENUM in B.6.
- created_at — used for acyclicity ordering: src.created_at MUST be
  STRICTLY LESS than dst.created_at, otherwise the edge would create
  a cycle (or imply causation backward in time).
- Unique constraint on (src_type, src_id, dst_type, dst_id, relation):
  duplicate edges with the same relation are no-ops; different
  relations between the same pair (e.g. A 'depends_on' B AND
  A 'evidences' B) are allowed.

Acyclicity enforcement: src.created_at < dst.created_at is enforced at
the app layer by `app/evidence/acyclicity.py` (this commit) — no DB
trigger yet. Phase B.3 CausalGraph service will use the table for
queries; Phase B.6 promotes to ENUM relation_semantic.

The clock-skew tolerance for the acyclicity check is per ADR-004
v2.1: `clock_skew_tolerance: 5 seconds`. Edges where src.created_at
is within 5s of dst.created_at are treated as effectively-equal
(no-cycle pass through the edge), preventing race-condition false
positives from clock-jitter on the same wall-second insert.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Index, UniqueConstraint, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class CausalEdge(Base, TimestampMixin):
    """Directed edge in the causal DAG.

    Inserts go through `app/evidence/acyclicity.py` to enforce the
    src.created_at < dst.created_at invariant.
    """

    __tablename__ = "causal_edges"
    __table_args__ = (
        UniqueConstraint(
            "src_type",
            "src_id",
            "dst_type",
            "dst_id",
            "relation",
            name="uq_causal_edges_src_dst_relation",
        ),
        Index("ix_causal_edges_src", "src_type", "src_id"),
        Index("ix_causal_edges_dst", "dst_type", "dst_id"),
        Index("ix_causal_edges_relation", "relation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    src_type: Mapped[str] = mapped_column(String(50), nullable=False)
    src_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dst_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dst_id: Mapped[int] = mapped_column(Integer, nullable=False)
    relation: Mapped[str] = mapped_column(String(50), nullable=False)
    # Note: separate timestamps for the edge endpoints, captured at
    # insert time. Used for acyclicity check; redundant with the source
    # entities' created_at but stored locally so the check doesn't need
    # to JOIN through every entity table to compute.
    src_created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    dst_created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
