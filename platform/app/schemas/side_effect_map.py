"""Pydantic schemas for SideEffectMap.impact_deltas — Phase 1 redesign.

Per ADR-028 Decision 3 (revised): JSONB column at the DB level, validated
by Pydantic *discriminated union* at the write boundary. Each `dimension`
literal binds a sharply-typed variant — AI cannot quietly write `"$1.50"`
into a numeric latency field.

Self-adjoint with the rendering layer (FORMAL P12): the same model
produces `render_for_dashboard()` and `validator_rules()`. Drift test in
`tests/test_impact_delta_round_trip.py` catches divergence.

Stage 28.3 (Pydantic schema validator) prereq.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    """Base for all delta variants. Forbids extra fields so AI typos
    fail loud at deserialise time rather than producing partial-validation."""

    model_config = ConfigDict(extra="forbid")


class LatencyDelta(_Base):
    dimension: Literal["latency_ms"]
    before: float
    after: float
    confidence: Literal["measured", "estimated", "guess"]


class CostDelta(_Base):
    dimension: Literal["cost_usd"]
    before: Decimal
    after: Decimal
    confidence: Literal["measured", "estimated", "guess"]


class BlastRadiusFilesDelta(_Base):
    dimension: Literal["blast_radius_files"]
    before: int
    after: int
    confidence: Literal["measured", "estimated", "guess"]


class BlastRadiusUsersDelta(_Base):
    dimension: Literal["blast_radius_users"]
    before: int
    after: int
    confidence: Literal["measured", "estimated", "guess"]


class ReversibilityClassDelta(_Base):
    """A → trivially reversible … E → irreversible."""

    dimension: Literal["reversibility_class"]
    before: Literal["A", "B", "C", "D", "E"]
    after: Literal["A", "B", "C", "D", "E"]
    confidence: Literal["measured", "estimated", "guess"]


# Discriminated union over `dimension`. Pydantic picks the correct variant
# automatically by reading the discriminator field.
ImpactDelta = Annotated[
    Union[
        LatencyDelta,
        CostDelta,
        BlastRadiusFilesDelta,
        BlastRadiusUsersDelta,
        ReversibilityClassDelta,
    ],
    Field(discriminator="dimension"),
]


class ImpactDeltaList(_Base):
    """Wrapper to validate a list of deltas (typically 1–5 entries per
    side_effect_map row). Use `ImpactDeltaList(items=...)` to validate;
    use `.items` to read the typed list."""

    items: list[ImpactDelta] = Field(default_factory=list)

    def to_jsonb(self) -> list[dict]:
        """Serialise to a list of plain dicts suitable for JSONB storage."""
        return [item.model_dump(mode="json") for item in self.items]

    @classmethod
    def from_jsonb(cls, raw: list[dict] | None) -> "ImpactDeltaList":
        """Inverse of `to_jsonb`. NULL JSONB → empty list."""
        if raw is None:
            return cls(items=[])
        return cls(items=raw)


__all__ = [
    "LatencyDelta",
    "CostDelta",
    "BlastRadiusFilesDelta",
    "BlastRadiusUsersDelta",
    "ReversibilityClassDelta",
    "ImpactDelta",
    "ImpactDeltaList",
]
