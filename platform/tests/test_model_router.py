"""Tests for ModelRouter — Phase L3 Stage L3.4.

Pure-function decision tree: same inputs -> same ModelChoice.
Verifies the priority order and the sonnet_only override.
"""

from __future__ import annotations

from app.llm.model_router import (
    Ceremony,
    ModelChoice,
    ModelFamily,
    Reversibility,
    RoutingInputs,
    route,
)


def _i(
    ceremony: Ceremony = Ceremony.STANDARD,
    complexity: int = 50,
    reversibility: Reversibility = Reversibility.REVERSIBLE,
    autonomy: int = 3,
) -> RoutingInputs:
    return RoutingInputs(
        ceremony=ceremony,
        complexity_score=complexity,
        reversibility=reversibility,
        autonomy_level=autonomy,
    )


# --- Critical ceremony -> Opus -------------------------------------------


def test_critical_ceremony_routes_to_opus():
    result = route(_i(ceremony=Ceremony.CRITICAL))
    assert result.model_family == ModelFamily.OPUS
    assert result.reason_code == "critical_ceremony"


def test_critical_ceremony_overrides_low_complexity():
    """Even low-complexity tasks at CRITICAL ceremony go to Opus."""
    result = route(_i(ceremony=Ceremony.CRITICAL, complexity=1))
    assert result.model_family == ModelFamily.OPUS


# --- Irreversible change -> Opus -----------------------------------------


def test_irreversible_change_routes_to_opus():
    result = route(_i(reversibility=Reversibility.IRREVERSIBLE))
    assert result.model_family == ModelFamily.OPUS
    assert result.reason_code == "irreversible_change"


def test_irreversible_change_overrides_low_ceremony():
    """LIGHT ceremony but IRREVERSIBLE -> still Opus."""
    result = route(_i(
        ceremony=Ceremony.LIGHT, reversibility=Reversibility.IRREVERSIBLE
    ))
    assert result.model_family == ModelFamily.OPUS


def test_critical_ceremony_priority_over_irreversibility():
    """When both apply, critical_ceremony reason wins (alphabetical doc order)."""
    result = route(_i(
        ceremony=Ceremony.CRITICAL, reversibility=Reversibility.IRREVERSIBLE
    ))
    assert result.model_family == ModelFamily.OPUS
    assert result.reason_code == "critical_ceremony"


# --- FULL ceremony or high complexity -> Sonnet --------------------------


def test_full_ceremony_routes_to_sonnet():
    result = route(_i(ceremony=Ceremony.FULL))
    assert result.model_family == ModelFamily.SONNET
    assert result.reason_code == "full_ceremony"


def test_high_complexity_routes_to_sonnet():
    result = route(_i(complexity=80))
    assert result.model_family == ModelFamily.SONNET
    assert result.reason_code == "high_complexity"


def test_complexity_at_exact_threshold_routes_to_sonnet():
    """Boundary: complexity == threshold -> Sonnet (>=)."""
    result = route(_i(complexity=70))
    assert result.model_family == ModelFamily.SONNET


def test_complexity_just_below_threshold_routes_to_haiku():
    result = route(_i(complexity=69))
    assert result.model_family == ModelFamily.HAIKU


# --- Default -> Haiku ----------------------------------------------------


def test_default_low_complexity_routes_to_haiku():
    """STANDARD ceremony + medium-low complexity + REVERSIBLE -> Haiku."""
    result = route(_i(
        ceremony=Ceremony.STANDARD, complexity=20,
        reversibility=Reversibility.REVERSIBLE,
    ))
    assert result.model_family == ModelFamily.HAIKU
    assert result.reason_code == "default_low_complexity"


def test_light_ceremony_low_complexity_routes_to_haiku():
    result = route(_i(ceremony=Ceremony.LIGHT, complexity=10))
    assert result.model_family == ModelFamily.HAIKU


# --- Sonnet-only override (MVP) ------------------------------------------


def test_sonnet_only_mode_overrides_critical_ceremony():
    result = route(_i(ceremony=Ceremony.CRITICAL), sonnet_only_mode=True)
    assert result.model_family == ModelFamily.SONNET
    assert result.reason_code == "sonnet_only_mvp_override"


def test_sonnet_only_mode_overrides_irreversibility():
    result = route(
        _i(reversibility=Reversibility.IRREVERSIBLE),
        sonnet_only_mode=True,
    )
    assert result.model_family == ModelFamily.SONNET


def test_sonnet_only_mode_for_low_complexity():
    """Even Haiku-eligible inputs go to Sonnet in MVP mode."""
    result = route(
        _i(ceremony=Ceremony.LIGHT, complexity=1),
        sonnet_only_mode=True,
    )
    assert result.model_family == ModelFamily.SONNET


# --- Fallback chains -----------------------------------------------------


def test_opus_fallback_chain_is_sonnet_then_haiku():
    result = route(_i(ceremony=Ceremony.CRITICAL))
    assert result.fallback_chain == (ModelFamily.SONNET, ModelFamily.HAIKU)


def test_sonnet_fallback_chain_is_haiku_only():
    result = route(_i(ceremony=Ceremony.FULL))
    assert result.fallback_chain == (ModelFamily.HAIKU,)


def test_haiku_fallback_chain_is_empty():
    """Haiku is bottom of chain; no fallback (caller must BLOCK)."""
    result = route(_i(complexity=10))
    assert result.fallback_chain == ()


# --- Custom threshold argument -------------------------------------------


def test_custom_threshold_higher_routes_more_to_haiku():
    result = route(_i(complexity=70), high_complexity_threshold=90)
    assert result.model_family == ModelFamily.HAIKU


def test_custom_threshold_lower_routes_more_to_sonnet():
    result = route(_i(complexity=30), high_complexity_threshold=20)
    assert result.model_family == ModelFamily.SONNET


# --- Determinism (P6) ----------------------------------------------------


def test_determinism():
    inputs = _i(ceremony=Ceremony.FULL, complexity=80,
                reversibility=Reversibility.COMPENSATABLE, autonomy=4)
    r1 = route(inputs)
    r2 = route(inputs)
    r3 = route(inputs)
    assert r1 == r2 == r3


def test_model_choice_is_frozen_dataclass():
    result = route(_i())
    try:
        result.model_family = ModelFamily.OPUS  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("ModelChoice should be frozen")


def test_routing_inputs_is_frozen_dataclass():
    inputs = _i()
    try:
        inputs.complexity_score = 99  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("RoutingInputs should be frozen")
