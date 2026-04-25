"""Tests for ContextBudget — Phase L3 Stage L3.3.

Pure-Python tests of the MUST/SHOULD/NICE bucket-priority fitter.
Determinism, hard MUST guarantee, priority order, tie-breaking.
"""

from __future__ import annotations

from app.llm.context_budget import Bucket, ContextItem, fit


def _item(
    content: str = "x",
    bucket: Bucket = Bucket.SHOULD,
    priority: int = 0,
    source_ref: str | None = None,
    tokens: int = 1,
) -> ContextItem:
    return ContextItem(
        content=content,
        bucket=bucket,
        priority_within_bucket=priority,
        source_ref=source_ref if source_ref is not None else f"ref-{content}",
        token_count=tokens,
    )


# --- Empty / minimal cases ------------------------------------------------


def test_empty_items_returns_accepted_empty():
    result = fit([], budget_tokens=100)
    assert result.status == "ACCEPTED"
    assert result.included == ()
    assert result.excluded == ()
    assert result.total_tokens == 0
    assert result.budget_tokens == 100


def test_zero_budget_accepts_zero_token_items():
    """A 0-token MUST item fits in a 0-token budget."""
    items = [_item(tokens=0, bucket=Bucket.MUST)]
    result = fit(items, budget_tokens=0)
    assert result.status == "ACCEPTED"
    assert len(result.included) == 1


# --- MUST hard guarantee --------------------------------------------------


def test_must_within_budget_admitted():
    items = [
        _item(bucket=Bucket.MUST, tokens=10),
        _item(bucket=Bucket.MUST, tokens=20),
    ]
    result = fit(items, budget_tokens=100)
    assert result.status == "ACCEPTED"
    assert len(result.included) == 2
    assert result.total_tokens == 30


def test_must_exactly_at_budget_admitted():
    items = [_item(bucket=Bucket.MUST, tokens=50)]
    result = fit(items, budget_tokens=50)
    assert result.status == "ACCEPTED"
    assert result.total_tokens == 50


def test_must_exceeds_budget_returns_rejected_no_partial_admit():
    """Hard guarantee: never partial-admit MUST."""
    items = [
        _item(bucket=Bucket.MUST, tokens=60, source_ref="a"),
        _item(bucket=Bucket.MUST, tokens=60, source_ref="b"),
        _item(bucket=Bucket.SHOULD, tokens=10, source_ref="c"),
    ]
    result = fit(items, budget_tokens=100)
    assert result.status == "REJECTED"
    assert result.reason and "must_exceeds_budget" in result.reason
    assert result.included == ()
    # All items excluded — caller MUST decompose, not partial-admit.
    assert len(result.excluded) == 3


def test_must_overflow_reason_surfaces_numbers():
    items = [_item(bucket=Bucket.MUST, tokens=200)]
    result = fit(items, budget_tokens=100)
    assert "200" in (result.reason or "")
    assert "100" in (result.reason or "")


# --- SHOULD/NICE priority + greedy fit ------------------------------------


def test_should_admitted_in_priority_order():
    """Higher priority_within_bucket admitted first."""
    items = [
        _item(bucket=Bucket.SHOULD, priority=1, tokens=10, source_ref="low"),
        _item(bucket=Bucket.SHOULD, priority=10, tokens=10, source_ref="high"),
        _item(bucket=Bucket.SHOULD, priority=5, tokens=10, source_ref="mid"),
    ]
    result = fit(items, budget_tokens=15)
    # Budget fits 1 of 3; priority=10 wins.
    assert result.status == "ACCEPTED"
    assert len(result.included) == 1
    assert result.included[0].source_ref == "high"


def test_must_first_then_should_then_nice():
    """Bucket order: all MUST, then SHOULD by priority, then NICE."""
    items = [
        _item(bucket=Bucket.NICE, priority=10, tokens=5, source_ref="nice-high"),
        _item(bucket=Bucket.SHOULD, priority=10, tokens=5, source_ref="should-high"),
        _item(bucket=Bucket.MUST, priority=1, tokens=5, source_ref="must-low"),
    ]
    result = fit(items, budget_tokens=15)
    assert result.status == "ACCEPTED"
    refs = [i.source_ref for i in result.included]
    # MUST first (regardless of priority), then SHOULD, then NICE.
    assert refs[0] == "must-low"
    assert refs[1] == "should-high"
    assert refs[2] == "nice-high"


def test_should_excluded_when_budget_exhausted():
    items = [
        _item(bucket=Bucket.MUST, tokens=80),
        _item(bucket=Bucket.SHOULD, priority=1, tokens=30, source_ref="big"),
        _item(bucket=Bucket.SHOULD, priority=2, tokens=10, source_ref="small"),
    ]
    result = fit(items, budget_tokens=100)
    # MUST takes 80; remaining 20.
    # Priority 2 admitted first (10 tokens fits); priority 1 (30) excluded.
    assert result.status == "ACCEPTED"
    refs_in = sorted(i.source_ref for i in result.included)
    assert refs_in == sorted(["src-content-not-set", "small"]) or "small" in refs_in
    # Verify "big" was excluded
    refs_out = [i.source_ref for i in result.excluded]
    assert "big" in refs_out


def test_nice_items_only_admitted_after_should():
    items = [
        _item(bucket=Bucket.SHOULD, priority=5, tokens=50, source_ref="should"),
        _item(bucket=Bucket.NICE, priority=10, tokens=10, source_ref="nice"),
    ]
    result = fit(items, budget_tokens=70)
    refs = [i.source_ref for i in result.included]
    # SHOULD admitted first
    assert refs[0] == "should"
    assert "nice" in refs


# --- Tie-breaking ----------------------------------------------------------


def test_same_priority_tied_by_source_ref_ascending():
    """When priority is equal, source_ref ascending breaks the tie."""
    items = [
        _item(bucket=Bucket.SHOULD, priority=5, tokens=5, source_ref="b-second"),
        _item(bucket=Bucket.SHOULD, priority=5, tokens=5, source_ref="a-first"),
        _item(bucket=Bucket.SHOULD, priority=5, tokens=5, source_ref="c-third"),
    ]
    # Budget for exactly 2 of the 3
    result = fit(items, budget_tokens=10)
    refs = [i.source_ref for i in result.included]
    assert refs == ["a-first", "b-second"]


# --- Determinism (P6) ------------------------------------------------------


def test_same_inputs_same_result_across_calls():
    items = [
        _item(bucket=Bucket.MUST, priority=1, tokens=10, source_ref="m1"),
        _item(bucket=Bucket.SHOULD, priority=2, tokens=20, source_ref="s1"),
        _item(bucket=Bucket.NICE, priority=3, tokens=5, source_ref="n1"),
    ]
    r1 = fit(items, budget_tokens=50)
    r2 = fit(items, budget_tokens=50)
    r3 = fit(items, budget_tokens=50)
    assert r1 == r2 == r3


def test_input_order_does_not_affect_result():
    items_a = [
        _item(bucket=Bucket.SHOULD, priority=5, tokens=5, source_ref="a"),
        _item(bucket=Bucket.SHOULD, priority=5, tokens=5, source_ref="b"),
        _item(bucket=Bucket.SHOULD, priority=10, tokens=5, source_ref="c"),
    ]
    items_b = list(reversed(items_a))
    r_a = fit(items_a, budget_tokens=10)
    r_b = fit(items_b, budget_tokens=10)
    # Same set of admitted items + same total
    refs_a = sorted(i.source_ref for i in r_a.included)
    refs_b = sorted(i.source_ref for i in r_b.included)
    assert refs_a == refs_b
    assert r_a.total_tokens == r_b.total_tokens


def test_fit_result_is_frozen_dataclass():
    """FitResult is immutable per design (caller cannot mutate after fit)."""
    items = [_item()]
    result = fit(items, budget_tokens=10)
    try:
        result.status = "MUTATED"  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("FitResult should be frozen")
