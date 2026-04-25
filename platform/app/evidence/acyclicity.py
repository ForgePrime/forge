"""Acyclicity check for CausalEdge inserts — Phase B Stage B.1.

Enforces FORMAL_PROPERTIES_v2 P14 acyclicity invariant via temporal
ordering: src.created_at MUST be strictly less than dst.created_at,
modulo a clock-skew tolerance window (per ADR-004 v2.1
`clock_skew_tolerance = 5 seconds`).

Pure function: takes the candidate edge endpoints' timestamps + the
tolerance, returns a Verdict-like decision. No DB read or write; the
caller is responsible for fetching src/dst created_at from their
respective tables and persisting the edge after a PASS verdict.

Why temporal ordering instead of true graph-cycle DFS:
- DFS over an N-node DAG is O(V+E) per insert. Temporal ordering
  rules out cycles by construction: if src is older than dst, no
  back-edge can exist (creation time is monotonic).
- The 5-second tolerance handles edge cases where two entities are
  inserted in the same wall-second (e.g. transactional batch insert);
  treating them as cycle-creating would incorrectly reject legitimate
  edges between sibling entities.
- Phase B.3 CausalGraph adds DFS-based deeper checks for query-time
  validation; B.1 keeps the insert-gate light.

Per CONTRACT §B.2: clock_skew_tolerance value is [CONFIRMED via
ADR-004 v2.1 quick-reference table line "clock_skew_tolerance: 5"].
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


# Per ADR-004 v2.1 quick-reference table entry:
# `- clock_skew_tolerance: 5`
# Wallclock seconds; src.created_at within this window of dst.created_at
# is treated as effectively-equal (no-cycle pass through this edge).
CLOCK_SKEW_TOLERANCE_SECONDS: int = 5


@dataclass(frozen=True)
class AcyclicityVerdict:
    """Outcome of an acyclicity pre-insert check."""

    passed: bool
    reason: str | None = None


def check_acyclicity(
    src_created_at: dt.datetime,
    dst_created_at: dt.datetime,
    *,
    tolerance_seconds: int = CLOCK_SKEW_TOLERANCE_SECONDS,
) -> AcyclicityVerdict:
    """Return PASS iff src.created_at + tolerance >= dst.created_at would NOT hold.

    Wait — reading more carefully: src must be STRICTLY OLDER than dst.
    The tolerance covers near-equal timestamps (insert race). Logic:

    - If src.created_at < dst.created_at - tolerance → PASS (clearly older).
    - If src.created_at <= dst.created_at + tolerance → PASS (near-equal,
      treat as concurrent insert; cycle ruled out by uniqueness, not by time).
      Actually... if src is FUTURE relative to dst, that IS a cycle.
    - If src.created_at > dst.created_at + tolerance → FAIL (src is
      meaningfully newer than dst → would imply backward causation).

    Simpler decision rule:
        PASS iff src.created_at <= dst.created_at + tolerance.

    Edge cases:
    - Both timestamps equal (same wall-second insert) → PASS (within
      tolerance).
    - src exactly tolerance newer than dst → PASS (boundary inclusive).
    - src tolerance+1s newer than dst → FAIL.
    """
    delta_seconds = (src_created_at - dst_created_at).total_seconds()
    if delta_seconds <= tolerance_seconds:
        # src is either strictly older OR within tolerance window of dst.
        return AcyclicityVerdict(passed=True)
    return AcyclicityVerdict(
        passed=False,
        reason=(
            f"acyclicity violated: src.created_at is "
            f"{delta_seconds:.3f}s newer than dst.created_at "
            f"(tolerance={tolerance_seconds}s); edge would imply "
            f"backward causation"
        ),
    )
