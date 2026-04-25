"""Round-trip + discriminated-union tests for ImpactDelta — Stage 28.3 prereq.

Per ADR-028 Decision 3: validates that each variant of ImpactDelta survives
encode → JSONB-equivalent dict → decode = identity. Catches:
  - silent type coercion (e.g. AI writing "$1.50" into a numeric Cost field)
  - wrong-variant matching (Pydantic picks the right model from discriminator)
  - shape drift (extra fields rejected per `extra="forbid"`)
  - missing/wrong discriminator value

These are the deterministic-gate tests that constitute G_5.1's Pydantic-side
ExitGate per PLAN_PHASE1_UX_INTEGRATION.md §5.1.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.side_effect_map import (
    BlastRadiusFilesDelta,
    BlastRadiusUsersDelta,
    CostDelta,
    ImpactDelta,
    ImpactDeltaList,
    LatencyDelta,
    ReversibilityClassDelta,
)

_adapter: TypeAdapter[ImpactDelta] = TypeAdapter(ImpactDelta)


# --- Round-trip per variant -------------------------------------------------


def test_latency_round_trip():
    raw = {"dimension": "latency_ms", "before": 100.0, "after": 250.5, "confidence": "measured"}
    parsed = _adapter.validate_python(raw)
    assert isinstance(parsed, LatencyDelta)
    assert parsed.before == 100.0
    assert parsed.after == 250.5
    serialised = parsed.model_dump(mode="json")
    assert serialised == raw


def test_cost_round_trip_decimal_precision():
    raw = {"dimension": "cost_usd", "before": "1.50", "after": "2.75", "confidence": "estimated"}
    parsed = _adapter.validate_python(raw)
    assert isinstance(parsed, CostDelta)
    assert parsed.before == Decimal("1.50")
    assert parsed.after == Decimal("2.75")


def test_blast_radius_files_round_trip():
    raw = {"dimension": "blast_radius_files", "before": 3, "after": 12, "confidence": "measured"}
    parsed = _adapter.validate_python(raw)
    assert isinstance(parsed, BlastRadiusFilesDelta)
    assert parsed.before == 3
    assert parsed.after == 12


def test_blast_radius_users_round_trip():
    raw = {"dimension": "blast_radius_users", "before": 0, "after": 1500, "confidence": "guess"}
    parsed = _adapter.validate_python(raw)
    assert isinstance(parsed, BlastRadiusUsersDelta)


def test_reversibility_class_round_trip():
    raw = {"dimension": "reversibility_class", "before": "A", "after": "C", "confidence": "estimated"}
    parsed = _adapter.validate_python(raw)
    assert isinstance(parsed, ReversibilityClassDelta)
    assert parsed.before == "A"
    assert parsed.after == "C"


# --- Discriminator behaviour ------------------------------------------------


def test_discriminator_picks_right_variant():
    """Pydantic must pick the correct variant from the discriminator alone."""
    raw_latency = {"dimension": "latency_ms", "before": 1.0, "after": 2.0, "confidence": "measured"}
    raw_cost = {"dimension": "cost_usd", "before": "1.0", "after": "2.0", "confidence": "measured"}
    assert isinstance(_adapter.validate_python(raw_latency), LatencyDelta)
    assert isinstance(_adapter.validate_python(raw_cost), CostDelta)


def test_unknown_dimension_rejected():
    """A dimension value outside the 5 closed options must fail validation."""
    with pytest.raises(ValidationError):
        _adapter.validate_python({"dimension": "magic", "before": 1, "after": 2, "confidence": "measured"})


def test_missing_discriminator_rejected():
    with pytest.raises(ValidationError):
        _adapter.validate_python({"before": 1.0, "after": 2.0, "confidence": "measured"})


# --- Wrong-type-into-correct-variant rejected (the AI silent-fill defense) -


def test_string_into_numeric_latency_rejected():
    """The whole point of discriminated union: '$1.50' (string) into LatencyDelta
    (numeric) must fail loud. Without discriminated union, it could quietly
    coerce or pick the wrong variant."""
    with pytest.raises(ValidationError):
        _adapter.validate_python({
            "dimension": "latency_ms",
            "before": "$1.50",  # bogus
            "after": 2.0,
            "confidence": "measured",
        })


def test_invalid_reversibility_class_rejected():
    with pytest.raises(ValidationError):
        _adapter.validate_python({
            "dimension": "reversibility_class",
            "before": "Z",  # not in A..E
            "after": "A",
            "confidence": "measured",
        })


def test_invalid_confidence_rejected():
    with pytest.raises(ValidationError):
        _adapter.validate_python({
            "dimension": "latency_ms",
            "before": 1.0, "after": 2.0,
            "confidence": "high",  # must be measured/estimated/guess
        })


def test_extra_field_rejected():
    """`extra='forbid'` so AI-injected unknown fields fail loud."""
    with pytest.raises(ValidationError):
        _adapter.validate_python({
            "dimension": "latency_ms",
            "before": 1.0, "after": 2.0,
            "confidence": "measured",
            "extra_field_not_in_schema": "surprise",
        })


# --- ImpactDeltaList wrapper (multi-delta JSONB blob) ----------------------


def test_impact_delta_list_to_jsonb_round_trip():
    """Full list round-trip mirroring the JSONB storage path."""
    deltas = [
        {"dimension": "latency_ms", "before": 100.0, "after": 200.0, "confidence": "measured"},
        {"dimension": "cost_usd", "before": "0.10", "after": "0.25", "confidence": "estimated"},
        {"dimension": "reversibility_class", "before": "A", "after": "C", "confidence": "guess"},
    ]
    parsed = ImpactDeltaList(items=deltas)
    serialised = parsed.to_jsonb()
    re_parsed = ImpactDeltaList.from_jsonb(serialised)
    re_serialised = re_parsed.to_jsonb()
    assert serialised == re_serialised  # encode → decode → encode = identity


def test_impact_delta_list_from_null_jsonb():
    parsed = ImpactDeltaList.from_jsonb(None)
    assert parsed.items == []
    assert parsed.to_jsonb() == []


def test_impact_delta_list_empty():
    parsed = ImpactDeltaList(items=[])
    assert parsed.to_jsonb() == []


# --- Determinism (FORMAL P6) -----------------------------------------------


def test_round_trip_is_deterministic():
    """Same input → identical bytes across calls."""
    raw = {"dimension": "cost_usd", "before": "1.50", "after": "2.75", "confidence": "measured"}
    a = _adapter.validate_python(raw).model_dump(mode="json")
    b = _adapter.validate_python(raw).model_dump(mode="json")
    c = _adapter.validate_python(raw).model_dump(mode="json")
    assert a == b == c


# --- Hand-rolled fuzz (Hypothesis substitute, sufficient coverage) ---------


@pytest.mark.parametrize("dimension,before,after,confidence", [
    ("latency_ms", 0.0, 1000.0, "measured"),
    ("latency_ms", 9999.99, 0.001, "guess"),
    ("cost_usd", "0.00", "1000000.0000", "estimated"),
    ("blast_radius_files", 1, 1, "measured"),
    ("blast_radius_files", 0, 99999, "guess"),
    ("blast_radius_users", 0, 0, "estimated"),
    ("reversibility_class", "A", "B", "measured"),
    ("reversibility_class", "E", "A", "estimated"),  # mitigation flow: improved
    ("reversibility_class", "A", "E", "guess"),       # regression flow: worsened
])
def test_parametrised_round_trip_combinations(dimension, before, after, confidence):
    raw = {"dimension": dimension, "before": before, "after": after, "confidence": confidence}
    parsed = _adapter.validate_python(raw)
    serialised = parsed.model_dump(mode="json")
    # Decimal serialises to string in mode='json'; compare semantically not literally
    re_parsed = _adapter.validate_python(serialised)
    assert parsed == re_parsed
