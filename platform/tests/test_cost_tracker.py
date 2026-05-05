"""Tests for CostTracker + BudgetGuard — Phase L3 Stage L3.6.

Pure-function tests of cost formula + budget evaluation. No DB.
Decimal arithmetic for exact-match assertions.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.llm.cost_tracker import (
    DEFAULT_PRICE_TABLE,
    BudgetDecision,
    BudgetVerdict,
    CostEstimate,
    TokenPrice,
    compute_cost,
    evaluate_budget,
)


# --- compute_cost() ------------------------------------------------------


def test_compute_cost_zero_tokens_zero_cost():
    estimate = compute_cost(
        model_family="haiku",
        input_tokens=0,
        output_tokens=0,
        price_table=DEFAULT_PRICE_TABLE,
    )
    assert estimate.cost_usd == Decimal("0")
    assert estimate.input_tokens == 0
    assert estimate.output_tokens == 0
    assert estimate.model_family == "haiku"


def test_compute_cost_haiku_known_values():
    """1000 input + 1000 output on haiku price table."""
    estimate = compute_cost(
        model_family="haiku",
        input_tokens=1000,
        output_tokens=1000,
        price_table=DEFAULT_PRICE_TABLE,
    )
    # input: 1000 * 0.001 / 1000 = 0.001
    # output: 1000 * 0.005 / 1000 = 0.005
    # total: 0.006
    assert estimate.cost_usd == Decimal("0.006")


def test_compute_cost_sonnet_known_values():
    """1000+1000 on sonnet table."""
    estimate = compute_cost(
        model_family="sonnet",
        input_tokens=1000,
        output_tokens=1000,
        price_table=DEFAULT_PRICE_TABLE,
    )
    # input: 1000 * 0.003 / 1000 = 0.003
    # output: 1000 * 0.015 / 1000 = 0.015
    # total: 0.018
    assert estimate.cost_usd == Decimal("0.018")


def test_compute_cost_opus_known_values():
    estimate = compute_cost(
        model_family="opus",
        input_tokens=1000,
        output_tokens=1000,
        price_table=DEFAULT_PRICE_TABLE,
    )
    # input: 1000 * 0.015 / 1000 = 0.015
    # output: 1000 * 0.075 / 1000 = 0.075
    # total: 0.090
    assert estimate.cost_usd == Decimal("0.090")


def test_compute_cost_scales_linearly():
    """10x tokens -> 10x cost."""
    e1 = compute_cost(
        model_family="sonnet", input_tokens=100, output_tokens=100,
        price_table=DEFAULT_PRICE_TABLE,
    )
    e10 = compute_cost(
        model_family="sonnet", input_tokens=1000, output_tokens=1000,
        price_table=DEFAULT_PRICE_TABLE,
    )
    assert e10.cost_usd == e1.cost_usd * 10


def test_compute_cost_unknown_model_raises():
    with pytest.raises(KeyError, match="missing entry"):
        compute_cost(
            model_family="gpt-4",  # not in price table
            input_tokens=100, output_tokens=100,
            price_table=DEFAULT_PRICE_TABLE,
        )


def test_compute_cost_negative_tokens_raises():
    with pytest.raises(ValueError, match="non-negative"):
        compute_cost(
            model_family="haiku", input_tokens=-1, output_tokens=100,
            price_table=DEFAULT_PRICE_TABLE,
        )


def test_compute_cost_custom_price_table():
    """Caller can pass synthetic prices for tests."""
    table = {
        "test_model": TokenPrice(
            input_per_1k_usd=Decimal("1"),
            output_per_1k_usd=Decimal("2"),
        )
    }
    estimate = compute_cost(
        model_family="test_model",
        input_tokens=2000, output_tokens=500,
        price_table=table,
    )
    # input: 2000 * 1 / 1000 = 2
    # output: 500 * 2 / 1000 = 1
    # total: 3
    assert estimate.cost_usd == Decimal("3")


# --- evaluate_budget() — pre-flight cases --------------------------------


def test_budget_pass_within_limit():
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("0.50"),
        next_call_estimate_usd=Decimal("0.30"),
        tau_cost_usd=Decimal("2.00"),
    )
    assert d.verdict == BudgetVerdict.PASS
    assert "within budget" in d.reason


def test_budget_exact_limit_passes():
    """projected == tau_cost is OK (boundary inclusive)."""
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("1.50"),
        next_call_estimate_usd=Decimal("0.50"),
        tau_cost_usd=Decimal("2.00"),
    )
    # 1.50 + 0.50 = 2.00 == tau (inclusive)
    assert d.verdict == BudgetVerdict.PASS


def test_budget_just_over_limit_rejected():
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("1.50"),
        next_call_estimate_usd=Decimal("0.51"),
        tau_cost_usd=Decimal("2.00"),
    )
    # 1.50 + 0.51 = 2.01 > 2.00
    assert d.verdict == BudgetVerdict.REJECTED
    assert "projected_cost_exceeds_tau_cost" in d.reason


def test_budget_zero_cumulative_large_estimate_rejected():
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("0"),
        next_call_estimate_usd=Decimal("3.00"),
        tau_cost_usd=Decimal("2.00"),
    )
    assert d.verdict == BudgetVerdict.REJECTED


# --- evaluate_budget() — post-hoc detection ------------------------------


def test_post_hoc_actual_within_15x_warns_no():
    """Actual + cumulative <= 1.5*tau -> PASS (no warn)."""
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("0"),
        next_call_estimate_usd=Decimal("0"),
        tau_cost_usd=Decimal("2.00"),
        post_hoc_actual_usd=Decimal("2.50"),  # 2.5 <= 1.5*2 = 3
    )
    assert d.verdict == BudgetVerdict.PASS


def test_post_hoc_actual_above_15x_warns():
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("0"),
        next_call_estimate_usd=Decimal("0"),
        tau_cost_usd=Decimal("2.00"),
        post_hoc_actual_usd=Decimal("4.00"),  # 4 > 1.5*2 = 3
    )
    assert d.verdict == BudgetVerdict.WARN_POST_HOC
    assert "post-hoc overrun" in d.reason


def test_post_hoc_with_cumulative_pushes_over():
    """Cumulative + post_hoc actual together exceed threshold."""
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("2.50"),
        next_call_estimate_usd=Decimal("0"),
        tau_cost_usd=Decimal("2.00"),
        post_hoc_actual_usd=Decimal("1.00"),  # 2.5 + 1 = 3.5 > 3
    )
    assert d.verdict == BudgetVerdict.WARN_POST_HOC


def test_custom_post_hoc_overrun_factor():
    """Stricter factor (1.0x) catches earlier."""
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("0"),
        next_call_estimate_usd=Decimal("0"),
        tau_cost_usd=Decimal("2.00"),
        post_hoc_actual_usd=Decimal("2.10"),
        post_hoc_overrun_factor=Decimal("1.0"),
    )
    assert d.verdict == BudgetVerdict.WARN_POST_HOC


# --- Determinism (P6) ----------------------------------------------------


def test_compute_cost_determinism():
    args = dict(
        model_family="sonnet",
        input_tokens=12345,
        output_tokens=6789,
        price_table=DEFAULT_PRICE_TABLE,
    )
    e1 = compute_cost(**args)
    e2 = compute_cost(**args)
    e3 = compute_cost(**args)
    assert e1 == e2 == e3


def test_evaluate_budget_determinism():
    args = dict(
        cumulative_cost_usd=Decimal("1.50"),
        next_call_estimate_usd=Decimal("0.30"),
        tau_cost_usd=Decimal("2.00"),
    )
    d1 = evaluate_budget(**args)
    d2 = evaluate_budget(**args)
    assert d1 == d2


def test_cost_estimate_is_frozen_dataclass():
    estimate = compute_cost(
        model_family="haiku", input_tokens=10, output_tokens=10,
        price_table=DEFAULT_PRICE_TABLE,
    )
    try:
        estimate.cost_usd = Decimal("999")  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("CostEstimate should be frozen")


def test_budget_decision_is_frozen_dataclass():
    d = evaluate_budget(
        cumulative_cost_usd=Decimal("0"),
        next_call_estimate_usd=Decimal("0.5"),
        tau_cost_usd=Decimal("2.00"),
    )
    try:
        d.verdict = BudgetVerdict.REJECTED  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("BudgetDecision should be frozen")
