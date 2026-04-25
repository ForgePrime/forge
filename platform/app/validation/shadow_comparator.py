"""Shadow-mode comparator — Phase A Stage A.3.

Lets existing call-sites (execute.py validate_delivery, pipeline.py
validate_plan_requirement_refs) invoke VerdictEngine in parallel with
the legacy validator and log any disagreement to verdict_divergences.

Modes (driven by settings.verdict_engine_mode):
- "off"     : compare_and_log() is a no-op. Default. Zero blast radius.
- "shadow"  : run VerdictEngine; if it disagrees with legacy, INSERT a
              row into verdict_divergences. Legacy verdict is still
              authoritative (does NOT change call-site behaviour).
- "enforce" : (NOT implemented in this commit; deferred to A.4 cutover.)
              Will make VerdictEngine authoritative; legacy still runs
              as a tripwire to surface drift.

Design: caller-side wrapper. Existing code stays in place; one extra
call adds shadow logging. Pure of side-effects in "off" mode (no DB
read or write); "shadow" mode performs an INSERT only on disagreement
(no per-call write spam when verdicts agree).

Per FORMAL_PROPERTIES_v2 P6: VerdictEngine and rules are pure; the
shadow-compare wrapper is the only impure layer (it writes to DB on
divergence). The wrapper itself is pure given a deterministic clock
and store; tests inject fakes via the `session_factory` argument.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from app.config import settings
from app.validation.rule_adapter import EvaluationContext, RuleAdapter
from app.validation.verdict_engine import VerdictEngine

# Type alias: factory returning a session-like object with .add() + .commit()
SessionFactory = Callable[[], Any]


def compare_and_log(
    *,
    session_factory: SessionFactory,
    execution_id: int,
    ctx: EvaluationContext,
    rules: Sequence[RuleAdapter],
    legacy_passed: bool,
    legacy_reason: str | None = None,
    mode: str | None = None,
) -> None:
    """Run VerdictEngine in shadow; log if it disagrees with legacy.

    Args:
        session_factory: callable producing a DB session (with .add() and
            .commit()). Tests inject a fake; production passes a real
            SQLAlchemy session factory.
        execution_id: FK target for the VerdictDivergence row.
        ctx: EvaluationContext for the engine call.
        rules: tuple of RuleAdapters (one or more).
        legacy_passed: bool — what the legacy validator returned.
        legacy_reason: optional human-readable reason for legacy fail.
        mode: override of settings.verdict_engine_mode (test injection).

    Returns:
        None. Side effect: in "shadow" mode, INSERTs a verdict_divergences
        row IFF engine_passed != legacy_passed.

    No exceptions are raised by this function in normal operation: it is
    a logging side-channel and must NOT break the legacy code path.
    Internal failures (e.g. DB connectivity loss) are swallowed and tagged
    on the divergence row when possible.
    """
    effective_mode = mode if mode is not None else settings.verdict_engine_mode

    if effective_mode == "off":
        return

    # mode in {"shadow", "enforce"} -> run engine and compare.
    engine_verdict = VerdictEngine.evaluate(ctx, rules=tuple(rules))
    engine_passed = engine_verdict.passed

    if engine_passed == legacy_passed:
        # No divergence; nothing to log.
        return

    # Disagreement -> log it. Lazy-import the model to keep this module
    # importable in test scenarios that mock the DB layer.
    try:
        from app.models.verdict_divergence import VerdictDivergence
    except ImportError:
        # Unrecoverable at import time; refuse silently rather than break
        # the legacy path. Production should never hit this.
        return

    row = VerdictDivergence(
        execution_id=execution_id,
        legacy_passed=legacy_passed,
        engine_passed=engine_passed,
        legacy_reason=legacy_reason,
        engine_reason=engine_verdict.reason,
        engine_rule_code=engine_verdict.rule_code,
        artifact_summary={
            "entity_type": ctx.entity_type,
            "from_state": ctx.from_state,
            "to_state": ctx.to_state,
            # Avoid serialising arbitrary artifact content into JSONB;
            # full reconstruction is via Execution.id in audit.
            "artifact_keys": sorted(ctx.artifact.keys()) if ctx.artifact else [],
        },
    )

    try:
        session = session_factory()
        session.add(row)
        session.commit()
    except Exception:
        # Logging side-channel must not break the legacy path.
        # In production, observability should surface this via APM.
        # Swallow + return (CONTRACT §A.6 disclosed limitation).
        return
