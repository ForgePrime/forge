"""End-to-end integration test for Phase A validation stack.

Composes: GateRegistry + VerdictEngine + RuleAdapters + shadow_comparator
+ FakeSession. Demonstrates that the Phase A cutover refactor pattern
works correctly across all three modes (off / shadow / enforce) for a
realistic Decision state transition.

This test does NOT require a running platform or live DB. It exercises
the same code paths that production execute.py / pipeline.py would
exercise after A.4 cutover, using an in-memory session fake.

Per CONTRACT §B.8 [ASSUMED: agent-analysis] — same-turn integration of
same-turn-authored components. Distinct-actor review still required.
"""

from __future__ import annotations

from typing import Any

from app.validation import gate_registry as gr
from app.validation.rule_adapter import EvaluationContext
from app.validation.shadow_comparator import compare_and_log


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits: int = 0

    def add(self, row: Any) -> None:
        self.added.append(row)

    def commit(self) -> None:
        self.commits += 1


def _decision_accept_ctx(*, evidence: tuple[int, ...], decision_id: int = 1) -> EvaluationContext:
    """Realistic context for a Decision ANALYZING -> ACCEPTED transition."""
    return EvaluationContext(
        entity_type="decision",
        entity_id=decision_id,
        from_state="ANALYZING",
        to_state="ACCEPTED",
        artifact={
            "recommendation": "rebuild the index quarterly",
            "issue": "stale index causes 3% slowdown",
            "type": "operational",
        },
        evidence=evidence,
    )


# --- Full-stack: registry lookup + engine + comparator ---------------------


def test_registry_lookup_returns_evidence_rule_for_decision_accept():
    """The GateRegistry has EvidenceLinkRequiredRule wired (among others)."""
    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")
    rule_codes = {r.rule_code for r in rules}
    assert "evidence_link_required" in rule_codes


def test_full_stack_enforce_mode_with_evidence_passes():
    """End-to-end: legacy says PASS, engine says PASS (evidence present),
    enforce mode uses engine verdict, no divergence logged."""
    session = _FakeSession()
    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")

    engine_verdict = compare_and_log(
        session_factory=lambda: session,
        execution_id=42,
        ctx=_decision_accept_ctx(evidence=(101, 102)),
        rules=rules,
        legacy_passed=True,
        legacy_reason=None,
        mode="enforce",
    )

    assert engine_verdict is not None
    assert engine_verdict.passed is True
    # No divergence -> no log row
    assert len(session.added) == 0


def test_full_stack_enforce_mode_blocks_evidence_free_decision():
    """End-to-end: legacy says PASS (oversight), engine says FAIL (no evidence),
    enforce mode blocks the transition with engine's authority."""
    session = _FakeSession()
    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")

    engine_verdict = compare_and_log(
        session_factory=lambda: session,
        execution_id=42,
        ctx=_decision_accept_ctx(evidence=()),  # NO evidence linked
        rules=rules,
        legacy_passed=True,  # legacy oversight
        mode="enforce",
    )

    # Engine catches what legacy missed.
    assert engine_verdict is not None
    assert engine_verdict.passed is False
    assert engine_verdict.rule_code == "evidence_link_required"
    assert engine_verdict.reason and "P16" in engine_verdict.reason

    # Divergence logged for audit
    assert len(session.added) == 1
    row = session.added[0]
    assert row.legacy_passed is True
    assert row.engine_passed is False


def test_full_stack_shadow_mode_legacy_authority_preserved():
    """Shadow mode: divergence logged, but caller workflow uses legacy
    (signified by 'shadow' mode in caller's if-branch)."""
    session = _FakeSession()
    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")

    engine_verdict = compare_and_log(
        session_factory=lambda: session,
        execution_id=42,
        ctx=_decision_accept_ctx(evidence=()),
        rules=rules,
        legacy_passed=True,
        mode="shadow",
    )

    # Divergence logged
    assert len(session.added) == 1

    # In shadow mode the *caller* would NOT use engine_verdict authoritatively;
    # we simulate the caller's pattern here.
    caller_authoritative_passed = (
        engine_verdict.passed
        if engine_verdict and "enforce" == "shadow"  # never True
        else True  # legacy_passed
    )
    assert caller_authoritative_passed is True


def test_full_stack_off_mode_zero_blast_radius():
    """Off mode: no engine call, no log, return None — production default."""
    session = _FakeSession()
    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")

    engine_verdict = compare_and_log(
        session_factory=lambda: session,
        execution_id=42,
        ctx=_decision_accept_ctx(evidence=()),
        rules=rules,
        legacy_passed=True,
        mode="off",
    )

    assert engine_verdict is None
    assert session.added == []
    assert session.commits == 0


# --- A.4 cutover-pattern simulation ----------------------------------------


def _simulate_call_site_pattern(
    *,
    mode: str,
    legacy_passed: bool,
    evidence: tuple[int, ...],
    session: _FakeSession,
) -> tuple[bool, str | None]:
    """Reproduce the pattern that A.4 cutover will apply at every call-site.

    Returns (final_passed, final_reason) where the caller-authoritative
    decision is computed per shadow_comparator.py docstring pattern.
    """
    rules = gr.lookup_rules("decision", "ANALYZING", "ACCEPTED")
    engine_verdict = compare_and_log(
        session_factory=lambda: session,
        execution_id=1,
        ctx=_decision_accept_ctx(evidence=evidence),
        rules=rules,
        legacy_passed=legacy_passed,
        legacy_reason="legacy says ok" if legacy_passed else "legacy says fail",
        mode=mode,
    )

    if engine_verdict is not None and mode == "enforce":
        return engine_verdict.passed, engine_verdict.reason
    return legacy_passed, "legacy_authoritative" if legacy_passed else "legacy says fail"


def test_cutover_pattern_off_uses_legacy():
    """mode=off: engine never runs; legacy authoritative."""
    session = _FakeSession()
    passed, reason = _simulate_call_site_pattern(
        mode="off", legacy_passed=True, evidence=(), session=session,
    )
    assert passed is True  # legacy
    assert "legacy" in (reason or "")


def test_cutover_pattern_shadow_uses_legacy_logs_divergence():
    """mode=shadow: legacy authoritative; engine disagreement logged."""
    session = _FakeSession()
    passed, reason = _simulate_call_site_pattern(
        mode="shadow", legacy_passed=True, evidence=(), session=session,
    )
    assert passed is True  # still legacy authoritative
    assert "legacy" in (reason or "")
    # But divergence is captured for review
    assert len(session.added) == 1


def test_cutover_pattern_enforce_uses_engine_overrides_legacy():
    """mode=enforce: engine authoritative; legacy oversight caught."""
    session = _FakeSession()
    passed, reason = _simulate_call_site_pattern(
        mode="enforce", legacy_passed=True, evidence=(), session=session,
    )
    assert passed is False  # engine overrides
    assert "P16" in (reason or "")
    assert len(session.added) == 1


def test_cutover_pattern_enforce_agrees_with_legacy_when_evidence_present():
    """mode=enforce + evidence present: both pass; no log."""
    session = _FakeSession()
    passed, reason = _simulate_call_site_pattern(
        mode="enforce", legacy_passed=True, evidence=(99,), session=session,
    )
    assert passed is True
    # No divergence
    assert session.added == []


def test_cutover_pattern_enforce_catches_legacy_false_negative():
    """mode=enforce + legacy says FAIL but engine says PASS:
    engine's PASS authority allows the transition the legacy would've blocked."""
    session = _FakeSession()
    passed, _ = _simulate_call_site_pattern(
        mode="enforce", legacy_passed=False, evidence=(99,), session=session,
    )
    # Engine says PASS (evidence present) -> overrides legacy FAIL
    assert passed is True
    # Divergence logged
    assert len(session.added) == 1


# --- Determinism across the full stack -------------------------------------


def test_full_stack_determinism():
    """Same inputs through the full stack -> identical outcome (P6).

    Critical: the integration of multiple components must preserve P6
    determinism that each component guarantees individually.
    """
    runs = []
    for _ in range(5):
        session = _FakeSession()
        passed, reason = _simulate_call_site_pattern(
            mode="enforce", legacy_passed=True, evidence=(), session=session,
        )
        runs.append((passed, reason, len(session.added)))
    # All runs identical
    assert all(r == runs[0] for r in runs)
