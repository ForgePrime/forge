"""Tests for CausalEdge acyclicity check — Phase B Stage B.1.

Pure-Python tests; no DB. Cover:
- Strictly older src → PASS.
- Equal timestamps → PASS (within tolerance).
- src up to tolerance newer → PASS (boundary inclusive).
- src tolerance+1ms newer → FAIL.
- Verdict.reason populated on FAIL.
- Custom tolerance argument respected.
- Determinism (P6).
"""

from __future__ import annotations

import datetime as dt

from app.evidence.acyclicity import (
    CLOCK_SKEW_TOLERANCE_SECONDS,
    AcyclicityVerdict,
    check_acyclicity,
)


def _ts(seconds: float) -> dt.datetime:
    """Helper: build a UTC datetime at offset `seconds` from epoch."""
    return dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=seconds)


def test_strictly_older_src_passes():
    """src clearly older than dst -> PASS."""
    v = check_acyclicity(_ts(0), _ts(100))
    assert v.passed is True
    assert v.reason is None


def test_equal_timestamps_pass():
    """Same wall-second insert -> within tolerance, PASS."""
    same = _ts(50)
    v = check_acyclicity(same, same)
    assert v.passed is True


def test_src_within_tolerance_newer_passes():
    """src up to CLOCK_SKEW_TOLERANCE_SECONDS newer -> PASS (boundary inclusive)."""
    v = check_acyclicity(_ts(105), _ts(100))
    # delta = +5s; equals tolerance -> PASS
    assert v.passed is True


def test_src_at_exact_tolerance_boundary_passes():
    v = check_acyclicity(_ts(100 + CLOCK_SKEW_TOLERANCE_SECONDS), _ts(100))
    assert v.passed is True


def test_src_just_outside_tolerance_fails():
    """src tolerance+1ms newer than dst -> FAIL."""
    v = check_acyclicity(
        _ts(100 + CLOCK_SKEW_TOLERANCE_SECONDS + 0.001),
        _ts(100),
    )
    assert v.passed is False
    assert v.reason is not None
    assert "backward causation" in v.reason
    assert "tolerance" in v.reason


def test_far_future_src_fails():
    """src 1h newer than dst -> FAIL with reason."""
    v = check_acyclicity(_ts(100 + 3600), _ts(100))
    assert v.passed is False
    assert "3600.0" in v.reason or "3600" in v.reason  # delta surfaced


def test_custom_tolerance_argument_respected():
    """Caller may supply a tighter tolerance (e.g. for stricter contexts)."""
    # With tolerance=0, even 1ms newer fails.
    v = check_acyclicity(_ts(100.001), _ts(100), tolerance_seconds=0)
    assert v.passed is False


def test_custom_tolerance_lenient_passes():
    """With wider tolerance, edge that would normally fail passes."""
    v = check_acyclicity(_ts(110), _ts(100), tolerance_seconds=15)
    assert v.passed is True


def test_determinism():
    """Same inputs -> same Verdict across calls (P6)."""
    src = _ts(100)
    dst = _ts(110)
    v1 = check_acyclicity(src, dst)
    v2 = check_acyclicity(src, dst)
    v3 = check_acyclicity(src, dst)
    assert v1 == v2 == v3


def test_verdict_is_frozen_dataclass():
    """AcyclicityVerdict is immutable per design."""
    v = check_acyclicity(_ts(0), _ts(100))
    try:
        v.passed = False  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        # If no exception, frozen=True is not enforced.
        raise AssertionError("AcyclicityVerdict should be frozen (immutable)")


def test_constant_value_matches_adr_004():
    """Phase A.1 spec wired to ADR-004 v2.1 clock_skew_tolerance: 5."""
    assert CLOCK_SKEW_TOLERANCE_SECONDS == 5
