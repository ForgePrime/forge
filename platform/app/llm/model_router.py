"""ModelRouter — Phase L3 Stage L3.4.

Pure deterministic decision tree mapping (ceremony, complexity,
reversibility, autonomy) -> ModelChoice.

Per PLAN_LLM_ORCHESTRATION L3.4 + ADR-006 (model pinning):
- CRITICAL ceremony OR IRREVERSIBLE change   -> Opus
- FULL ceremony OR high complexity           -> Sonnet
- Otherwise                                  -> Haiku

MVP override: env LLM_ROUTER_MODE=sonnet_only forces all routes to
Sonnet regardless of input. This is the MVP_SCOPE §L3 default until
benchmark scores >=0.6 on Task-bench-01/02/03 with full routing.

Fallback chain: if the chosen model is unavailable (caller's
responsibility to detect via provider error), the router exposes a
deterministic fallback chain Opus -> Sonnet -> Haiku. Fallback NEVER
goes UP (Haiku cannot fall back to Sonnet — that's a quality
escalation, not a degradation).

Determinism (P6): same inputs + same router_mode + same routing_table
-> same ModelChoice. The routing table is a frozen-at-import constant
loaded from app.config; runtime re-imports yield the same table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Ceremony(str, Enum):
    """Per ADR-002 task ceremony levels."""

    LIGHT = "LIGHT"
    STANDARD = "STANDARD"
    FULL = "FULL"
    CRITICAL = "CRITICAL"


class Reversibility(str, Enum):
    """Per FORMAL P5 / C.4."""

    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    RECONSTRUCTABLE = "RECONSTRUCTABLE"
    IRREVERSIBLE = "IRREVERSIBLE"


# Model identifiers. Concrete pin format per ADR-006:
# 'claude-opus-4-7:2026-04-15' etc. The router returns the family name;
# the caller resolves to the pinned version via app.config.
class ModelFamily(str, Enum):
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


# Default fallback chain (per PLAN L3.4): degrades from chosen ->
# successively cheaper / smaller. Only DOWNGRADE allowed; never upgrade.
_FALLBACK_CHAIN: dict[ModelFamily, tuple[ModelFamily, ...]] = {
    ModelFamily.OPUS: (ModelFamily.SONNET, ModelFamily.HAIKU),
    ModelFamily.SONNET: (ModelFamily.HAIKU,),
    ModelFamily.HAIKU: (),  # bottom of the chain; if unavailable -> BLOCKED
}


# High-complexity threshold per ADR-004 (calibration). Tasks with
# complexity_score >= this value are routed up at least to Sonnet.
# Ranges 0..100 by convention; default 70 = "harder than typical".
HIGH_COMPLEXITY_THRESHOLD: int = 70


@dataclass(frozen=True)
class RoutingInputs:
    """Snapshot of the 4 inputs the router sees at call time."""

    ceremony: Ceremony
    complexity_score: int  # 0..100
    reversibility: Reversibility
    autonomy_level: int  # L1..L5 (1..5)


@dataclass(frozen=True)
class ModelChoice:
    """Output of routing decision. Caller dispatches to model_family."""

    model_family: ModelFamily
    reason_code: str  # 'critical_ceremony' | 'irreversible_change' | etc.
    fallback_chain: tuple[ModelFamily, ...] = field(default_factory=tuple)


def route(
    inputs: RoutingInputs,
    *,
    sonnet_only_mode: bool = False,
    high_complexity_threshold: int = HIGH_COMPLEXITY_THRESHOLD,
) -> ModelChoice:
    """Deterministic routing decision tree.

    Args:
        inputs: RoutingInputs snapshot.
        sonnet_only_mode: if True, all routes return Sonnet (MVP override).
            Caller passes settings.llm_router_mode == 'sonnet_only'.
        high_complexity_threshold: per ADR-004; default 70.

    Returns:
        ModelChoice with chosen model, reason code, and fallback chain.

    Determinism: pure function over its arguments. No env/clock/network
    reads. Tests construct RoutingInputs explicitly.
    """
    if sonnet_only_mode:
        return ModelChoice(
            model_family=ModelFamily.SONNET,
            reason_code="sonnet_only_mvp_override",
            fallback_chain=_FALLBACK_CHAIN[ModelFamily.SONNET],
        )

    # CRITICAL ceremony OR IRREVERSIBLE change -> Opus
    if inputs.ceremony == Ceremony.CRITICAL:
        return ModelChoice(
            model_family=ModelFamily.OPUS,
            reason_code="critical_ceremony",
            fallback_chain=_FALLBACK_CHAIN[ModelFamily.OPUS],
        )
    if inputs.reversibility == Reversibility.IRREVERSIBLE:
        return ModelChoice(
            model_family=ModelFamily.OPUS,
            reason_code="irreversible_change",
            fallback_chain=_FALLBACK_CHAIN[ModelFamily.OPUS],
        )

    # FULL ceremony OR high complexity -> Sonnet
    if inputs.ceremony == Ceremony.FULL:
        return ModelChoice(
            model_family=ModelFamily.SONNET,
            reason_code="full_ceremony",
            fallback_chain=_FALLBACK_CHAIN[ModelFamily.SONNET],
        )
    if inputs.complexity_score >= high_complexity_threshold:
        return ModelChoice(
            model_family=ModelFamily.SONNET,
            reason_code="high_complexity",
            fallback_chain=_FALLBACK_CHAIN[ModelFamily.SONNET],
        )

    # Default: Haiku
    return ModelChoice(
        model_family=ModelFamily.HAIKU,
        reason_code="default_low_complexity",
        fallback_chain=_FALLBACK_CHAIN[ModelFamily.HAIKU],
    )
