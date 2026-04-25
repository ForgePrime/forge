"""epistemic_tag enum — Phase 1 redesign integration.

Per ADR-028 Decision 2 (revised): closed at 6 values. The Postgres ENUM
type already exists on the DB (created by Phase 1 migration §1); this
module exposes the Python-side enum + the SQLAlchemy column type that
maps to it WITHOUT trying to recreate the type (`create_type=False`).
"""

from __future__ import annotations

from enum import Enum
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM


class EpistemicTag(str, Enum):
    """6 closed values per ADR-028 D2 revised. Maps 1:1 to Postgres ENUM
    type `epistemic_tag` defined by the Phase 1 migration.

    Display layer renders hyphens (ADR-CITED, STEWARD-AUTHORED) but the
    DB stores underscores for ENUM identifier compatibility.
    """

    INVENTED = "INVENTED"                      # claim with no upstream source
    SPEC_DERIVED = "SPEC_DERIVED"              # cited spec/contract/SLA
    ADR_CITED = "ADR_CITED"                    # specific ADR reference
    EMPIRICALLY_OBSERVED = "EMPIRICALLY_OBSERVED"  # runtime observation
    TOOL_VERIFIED = "TOOL_VERIFIED"            # deterministic tool check
    STEWARD_AUTHORED = "STEWARD_AUTHORED"      # Steward sign-off recorded


# SQLAlchemy column type — references existing PG ENUM, does NOT recreate it.
# Use this in mapped_column declarations: mapped_column(epistemic_tag_pg_enum)
epistemic_tag_pg_enum = PG_ENUM(
    EpistemicTag,
    name="epistemic_tag",
    create_type=False,
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class ObjectiveStage(str, Enum):
    """4 closed values per ADR-028 D4 revised. Stored as VARCHAR(8) +
    CHECK constraint on the DB (not as PG ENUM type — see ADR-028 D4
    rationale: consistency with existing `objectives.status` pattern)."""

    KICKOFF = "KICKOFF"
    PLAN = "PLAN"
    EXEC = "EXEC"
    VERIFY = "VERIFY"


class AutonomyPinned(str, Enum):
    """4 closed values for `objectives.autonomy_pinned`. Stored as
    VARCHAR(8) + CHECK constraint (see Phase 1 migration §2)."""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
