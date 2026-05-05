"""CostTracker + BudgetGuard — Phase L3 Stage L3.6.

Pure-function portion: cost formula + budget evaluation.
DB-backed portion (llm_calls writes, execution_total aggregation
across DB rows) lands in a separate commit when the integration is
wired into mcp_server / api/execute.py.

Per PLAN_LLM_ORCHESTRATION L3.6 + ADR-006 price table:
    cost_usd = input_tokens * input_price_per_1k / 1000
             + output_tokens * output_price_per_1k / 1000

ADR-006 price table is per-model + version-pinned. This module accepts
a price-table mapping at call time so:
- Tests pass synthetic prices (deterministic).
- Production reads ADR-006 prices via app.config.

BudgetGuard evaluates whether a projected next call would push the
Execution's cumulative cost over τ_cost (per ADR-004 = $2 default for
MVP). Pre-flight halt prevents runaway; post-hoc detection of
overruns >1.5x τ_cost emits Finding (caller's responsibility, not
this module's — this module just exposes the verdict).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Mapping


@dataclass(frozen=True)
class TokenPrice:
    """Per-model price entry from ADR-006 price table.

    All prices in USD per 1000 tokens. Decimal for exact arithmetic.
    """

    input_per_1k_usd: Decimal
    output_per_1k_usd: Decimal


@dataclass(frozen=True)
class CostEstimate:
    """Pre-flight or post-hoc cost computation."""

    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    model_family: str  # ModelFamily.value (string)


class BudgetVerdict(str, Enum):
    PASS = "pass"
    REJECTED = "rejected"
    WARN_POST_HOC = "warn_post_hoc"  # actual > 1.5x τ_cost after the fact


@dataclass(frozen=True)
class BudgetDecision:
    """Output of BudgetGuard.evaluate()."""

    verdict: BudgetVerdict
    cumulative_cost_usd: Decimal
    next_call_estimate_usd: Decimal
    tau_cost_usd: Decimal
    reason: str


def compute_cost(
    *,
    model_family: str,
    input_tokens: int,
    output_tokens: int,
    price_table: Mapping[str, TokenPrice],
) -> CostEstimate:
    """Compute USD cost of a (would-be) call.

    Args:
        model_family: e.g. 'opus' / 'sonnet' / 'haiku'. Must be a key
            in price_table.
        input_tokens: tokens in the assembled prompt.
        output_tokens: tokens in the (estimated or actual) response.
        price_table: per-model TokenPrice mapping.

    Returns:
        CostEstimate. Raises KeyError if model_family unknown — caller
        should fail-fast on missing price entries (per CONTRACT §B.2).
    """
    if model_family not in price_table:
        raise KeyError(
            f"price_table missing entry for model_family={model_family!r}; "
            f"known: {sorted(price_table.keys())}"
        )
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError(
            f"token counts must be non-negative; got "
            f"input={input_tokens}, output={output_tokens}"
        )
    price = price_table[model_family]
    cost = (
        Decimal(input_tokens) * price.input_per_1k_usd / Decimal(1000)
        + Decimal(output_tokens) * price.output_per_1k_usd / Decimal(1000)
    )
    return CostEstimate(
        cost_usd=cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model_family=model_family,
    )


def evaluate_budget(
    *,
    cumulative_cost_usd: Decimal,
    next_call_estimate_usd: Decimal,
    tau_cost_usd: Decimal,
    post_hoc_actual_usd: Decimal | None = None,
    post_hoc_overrun_factor: Decimal = Decimal("1.5"),
) -> BudgetDecision:
    """Evaluate the budget for a pre-flight or post-hoc check.

    Args:
        cumulative_cost_usd: total USD already spent on this Execution
            (sum over its llm_calls rows).
        next_call_estimate_usd: estimate for the next call about to fire.
        tau_cost_usd: per-Execution cost ceiling per ADR-004.
        post_hoc_actual_usd: if provided, compare cumulative + actual
            vs tau_cost * post_hoc_overrun_factor (default 1.5x). When
            this exceeds the limit, return WARN_POST_HOC. Used by the
            caller after a call completes to detect surprise overruns.
        post_hoc_overrun_factor: default 1.5 — actual >1.5x τ_cost is
            an alert per L3.6 spec.

    Returns:
        BudgetDecision. Pure function over arguments.
    """
    # Post-hoc detection runs first (it's about completed cost, not
    # projected). When provided, takes precedence over pre-flight check
    # because we already spent the money.
    if post_hoc_actual_usd is not None:
        actual_total = cumulative_cost_usd + post_hoc_actual_usd
        threshold = tau_cost_usd * post_hoc_overrun_factor
        if actual_total > threshold:
            return BudgetDecision(
                verdict=BudgetVerdict.WARN_POST_HOC,
                cumulative_cost_usd=actual_total,
                next_call_estimate_usd=Decimal(0),
                tau_cost_usd=tau_cost_usd,
                reason=(
                    f"post-hoc overrun: actual ${actual_total} > "
                    f"{post_hoc_overrun_factor}x tau_cost (${threshold})"
                ),
            )

    # Pre-flight check: would the next call push us over tau_cost?
    projected = cumulative_cost_usd + next_call_estimate_usd
    if projected > tau_cost_usd:
        return BudgetDecision(
            verdict=BudgetVerdict.REJECTED,
            cumulative_cost_usd=cumulative_cost_usd,
            next_call_estimate_usd=next_call_estimate_usd,
            tau_cost_usd=tau_cost_usd,
            reason=(
                f"projected_cost_exceeds_tau_cost: "
                f"cumulative=${cumulative_cost_usd} + "
                f"estimate=${next_call_estimate_usd} = "
                f"${projected} > tau_cost=${tau_cost_usd}"
            ),
        )

    return BudgetDecision(
        verdict=BudgetVerdict.PASS,
        cumulative_cost_usd=cumulative_cost_usd,
        next_call_estimate_usd=next_call_estimate_usd,
        tau_cost_usd=tau_cost_usd,
        reason=f"projected ${projected} within budget ${tau_cost_usd}",
    )


# Default price table for testing + reference (real prices subject to
# provider changes; production loads from app.config / ADR-006 v2.1+).
# Values are reasonable estimates as of 2026 Anthropic pricing tiers.
DEFAULT_PRICE_TABLE: Mapping[str, TokenPrice] = {
    "opus": TokenPrice(
        input_per_1k_usd=Decimal("0.015"),
        output_per_1k_usd=Decimal("0.075"),
    ),
    "sonnet": TokenPrice(
        input_per_1k_usd=Decimal("0.003"),
        output_per_1k_usd=Decimal("0.015"),
    ),
    "haiku": TokenPrice(
        input_per_1k_usd=Decimal("0.001"),
        output_per_1k_usd=Decimal("0.005"),
    ),
}
