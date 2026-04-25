"""Tests for shadow-mode comparator — Phase A Stage A.3.

Exercises the three modes (off / shadow / enforce-stub) without
touching a real DB. Uses a FakeSession that records added rows for
inspection, avoiding pytest fixture / DB dependency.
"""

from __future__ import annotations

from typing import Any

from app.validation.rule_adapter import EvaluationContext, Verdict
from app.validation.rules import evidence_link_required
from app.validation.shadow_comparator import compare_and_log


class _FakeSession:
    """Minimal session double — captures .add() calls + commit count."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits: int = 0

    def add(self, row: Any) -> None:
        self.added.append(row)

    def commit(self) -> None:
        self.commits += 1


def _ctx(evidence: tuple[int, ...] = ()) -> EvaluationContext:
    return EvaluationContext(
        entity_type="decision",
        entity_id=1,
        from_state="ANALYZING",
        to_state="ACCEPTED",
        artifact={"recommendation": "test"},
        evidence=evidence,
    )


# --- Mode: off (default) ---------------------------------------------------


def test_off_mode_is_noop_no_engine_call_no_session_call():
    """In 'off' mode: no engine call, no session call, no exception."""
    session = _FakeSession()

    def factory():
        return session

    result = compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(),
        rules=(evidence_link_required,),
        legacy_passed=True,
        mode="off",
    )
    assert result is None
    assert session.added == []
    assert session.commits == 0


def test_off_mode_does_not_construct_session():
    """'off' mode short-circuits before factory is called."""
    factory_call_count = 0

    def factory():
        nonlocal factory_call_count
        factory_call_count += 1
        return _FakeSession()

    compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(),
        rules=(evidence_link_required,),
        legacy_passed=False,
        mode="off",
    )
    assert factory_call_count == 0


# --- Mode: shadow — engine + legacy AGREE -> no log -----------------------


def test_shadow_mode_no_log_when_both_pass():
    session = _FakeSession()

    def factory():
        return session

    # evidence non-empty -> engine PASSES; legacy_passed=True -> agree
    result = compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(evidence=(42,)),
        rules=(evidence_link_required,),
        legacy_passed=True,
        mode="shadow",
    )
    assert session.added == []
    assert session.commits == 0
    # Engine verdict still returned for diagnostic + enforce-pattern uniformity
    assert result is not None
    assert result.passed is True
    assert result.rule_code == "all_rules_passed"


def test_shadow_mode_no_log_when_both_fail():
    session = _FakeSession()

    def factory():
        return session

    # evidence empty -> engine FAILS; legacy_passed=False -> agree
    compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(evidence=()),
        rules=(evidence_link_required,),
        legacy_passed=False,
        mode="shadow",
    )
    assert session.added == []


# --- Mode: shadow — DISAGREE -> log a divergence row -----------------------


def test_shadow_mode_logs_when_engine_fails_but_legacy_passes():
    """Legacy says PASS, engine says FAIL -> divergence row inserted."""
    session = _FakeSession()

    def factory():
        return session

    # evidence empty -> engine FAILS; legacy_passed=True -> DISAGREE
    compare_and_log(
        session_factory=factory,
        execution_id=42,
        ctx=_ctx(evidence=()),
        rules=(evidence_link_required,),
        legacy_passed=True,
        legacy_reason="legacy validator allowed it",
        mode="shadow",
    )
    assert len(session.added) == 1
    assert session.commits == 1
    row = session.added[0]
    assert row.execution_id == 42
    assert row.legacy_passed is True
    assert row.engine_passed is False
    assert row.legacy_reason == "legacy validator allowed it"
    assert row.engine_rule_code == "evidence_link_required"
    assert row.artifact_summary == {
        "entity_type": "decision",
        "from_state": "ANALYZING",
        "to_state": "ACCEPTED",
        "artifact_keys": ["recommendation"],
    }


def test_shadow_mode_logs_when_engine_passes_but_legacy_fails():
    """Engine says PASS, legacy says FAIL -> divergence row inserted."""
    session = _FakeSession()

    def factory():
        return session

    # evidence non-empty -> engine PASSES; legacy_passed=False -> DISAGREE
    compare_and_log(
        session_factory=factory,
        execution_id=99,
        ctx=_ctx(evidence=(1, 2)),
        rules=(evidence_link_required,),
        legacy_passed=False,
        mode="shadow",
    )
    assert len(session.added) == 1
    row = session.added[0]
    assert row.legacy_passed is False
    assert row.engine_passed is True


# --- Resilience: DB error must NOT break legacy path ----------------------


def test_session_factory_failure_swallowed_silently():
    """Per CONTRACT §A.6 disclosure: shadow logging never breaks legacy path."""

    def factory():
        raise RuntimeError("DB unreachable")

    # No exception should propagate.
    compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(evidence=()),
        rules=(evidence_link_required,),
        legacy_passed=True,
        mode="shadow",
    )
    # Test passes if no exception raised.


def test_session_commit_failure_swallowed_silently():
    """Commit failure in shadow mode: legacy path must continue."""

    class _BrokenSession(_FakeSession):
        def commit(self) -> None:
            raise RuntimeError("disk full")

    session = _BrokenSession()

    def factory():
        return session

    compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(evidence=()),
        rules=(evidence_link_required,),
        legacy_passed=True,
        mode="shadow",
    )
    # No exception. The row was added (session.added populated) but commit
    # failed; that's the disclosed swallow-silently behaviour.
    assert len(session.added) == 1


# --- Mode: enforce — return engine verdict for caller authority -----------


def test_enforce_mode_returns_engine_verdict_when_engine_passes():
    """enforce mode: engine PASS -> caller uses engine.passed=True."""
    session = _FakeSession()

    def factory():
        return session

    result = compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(evidence=(42,)),
        rules=(evidence_link_required,),
        legacy_passed=True,
        mode="enforce",
    )
    assert result is not None
    assert result.passed is True
    # No divergence -> no log row
    assert session.added == []


def test_enforce_mode_returns_engine_verdict_when_engine_fails():
    """enforce: engine FAIL overrides legacy PASS; row logged."""
    session = _FakeSession()

    def factory():
        return session

    result = compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(evidence=()),
        rules=(evidence_link_required,),
        legacy_passed=True,  # legacy says pass, engine says fail
        mode="enforce",
    )
    assert result is not None
    assert result.passed is False
    assert result.rule_code == "evidence_link_required"
    # Divergence logged
    assert len(session.added) == 1


def test_enforce_mode_logging_failure_still_returns_verdict():
    """Even if DB logging fails, enforce mode preserves authority signal."""

    def factory():
        raise RuntimeError("DB unreachable")

    result = compare_and_log(
        session_factory=factory,
        execution_id=1,
        ctx=_ctx(evidence=()),
        rules=(evidence_link_required,),
        legacy_passed=True,  # disagrees with engine fail
        mode="enforce",
    )
    # Critical: enforce mode must NOT lose authority signal due to log failure.
    assert result is not None
    assert result.passed is False


# --- Multiple disagreements logged independently --------------------------


def test_each_call_logs_separately():
    session = _FakeSession()

    def factory():
        return session

    # Three disagreement calls -> three rows.
    for exec_id in [1, 2, 3]:
        compare_and_log(
            session_factory=factory,
            execution_id=exec_id,
            ctx=_ctx(evidence=()),
            rules=(evidence_link_required,),
            legacy_passed=True,  # legacy says pass; engine says fail
            mode="shadow",
        )
    assert len(session.added) == 3
    assert session.commits == 3
    assert [r.execution_id for r in session.added] == [1, 2, 3]
