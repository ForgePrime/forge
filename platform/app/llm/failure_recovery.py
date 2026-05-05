"""FailureRecovery — Phase L3 Stage L3.5.

Rule-based classification of LLM/tool errors -> recovery actions.
Deliberately NOT LLM-based (per PLAN_LLM_ORCHESTRATION + ECITP §2.8
prohibition on prior substitution): the recovery decision must be
deterministic given the error class.

Two-axis decision:
1. Classify the error: transient vs permanent.
2. Pick action based on classification + retry budgets.

Transient (retryable):
- Provider 5xx, network timeout, rate-limit (429), JSON parse error
  on output, schema-mismatch on tool args.

Permanent (BLOCKED):
- Authentication failure (401/403).
- Model deprecated.
- Budget exceeded.
- All-models-unavailable (after fallback chain exhausted).
- Schema-mismatch repeated 2x (caller's job to count).

Retry budget per MVP_SCOPE §L3: 1 retry on timeout, 2 retries on
malformed output. Configurable via arguments; defaults match MVP.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureClass(str, Enum):
    """Two-bucket classification of LLM call errors."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"


class ErrorCode(str, Enum):
    """Canonical error codes the classifier knows about.

    Caller maps provider-specific errors to these. Unknown codes default
    to PERMANENT (fail-safe) per CONTRACT §B.2 — better to BLOCK than to
    retry an unknown error class indefinitely.
    """

    # Transient
    PROVIDER_5XX = "provider_5xx"
    NETWORK_TIMEOUT = "network_timeout"
    RATE_LIMITED = "rate_limited"
    JSON_PARSE_ERROR = "json_parse_error"
    SCHEMA_MISMATCH = "schema_mismatch"
    # Permanent
    AUTH_FAILURE = "auth_failure"
    MODEL_DEPRECATED = "model_deprecated"
    BUDGET_EXCEEDED = "budget_exceeded"
    ALL_MODELS_UNAVAILABLE = "all_models_unavailable"
    UNKNOWN = "unknown"  # fail-safe default


_TRANSIENT_CODES: frozenset[ErrorCode] = frozenset({
    ErrorCode.PROVIDER_5XX,
    ErrorCode.NETWORK_TIMEOUT,
    ErrorCode.RATE_LIMITED,
    ErrorCode.JSON_PARSE_ERROR,
    ErrorCode.SCHEMA_MISMATCH,
})


class RecoveryAction(str, Enum):
    """What the dispatch loop should do next."""

    RETRY_SAME_PROMPT = "retry_same_prompt"
    RETRY_WITH_SCHEMA_REMINDER = "retry_with_schema_reminder"
    FALLBACK_MODEL = "fallback_model"
    BLOCK_EXECUTION = "block_execution"


@dataclass(frozen=True)
class RecoveryDecision:
    """Output of the recovery classifier."""

    action: RecoveryAction
    failure_class: FailureClass
    error_code: ErrorCode
    reason: str  # human-readable diagnostic


# Default budgets per MVP_SCOPE §L3.
DEFAULT_TRANSIENT_RETRY_BUDGET: int = 1
DEFAULT_MALFORMED_RETRY_BUDGET: int = 2


def classify(error_code: ErrorCode) -> FailureClass:
    """Map an error code to its failure class."""
    if error_code in _TRANSIENT_CODES:
        return FailureClass.TRANSIENT
    return FailureClass.PERMANENT


def decide(
    error_code: ErrorCode,
    *,
    retry_count: int,
    transient_retry_budget: int = DEFAULT_TRANSIENT_RETRY_BUDGET,
    malformed_retry_budget: int = DEFAULT_MALFORMED_RETRY_BUDGET,
) -> RecoveryDecision:
    """Decide next action for an LLM call failure.

    Args:
        error_code: ErrorCode reported by the dispatcher.
        retry_count: how many times this call has already been retried
            (0 on first failure).
        transient_retry_budget: max retries for generic transient errors.
        malformed_retry_budget: max retries for output-shape errors
            (where each retry adds a schema reminder to the prompt).

    Returns:
        RecoveryDecision with action + failure_class + reason.

    Determinism: pure function over arguments. No env/clock reads.
    """
    cls = classify(error_code)

    if cls == FailureClass.PERMANENT:
        # Permanent failures route immediately to BLOCKED. No fallback
        # for auth/budget/deprecated; for ALL_MODELS_UNAVAILABLE the
        # caller has already exhausted fallback chain (L3.4) before
        # reaching here.
        return RecoveryDecision(
            action=RecoveryAction.BLOCK_EXECUTION,
            failure_class=FailureClass.PERMANENT,
            error_code=error_code,
            reason=f"permanent failure {error_code.value}; no retry",
        )

    # Transient — pick action per error code + retry count.
    if error_code == ErrorCode.JSON_PARSE_ERROR or error_code == ErrorCode.SCHEMA_MISMATCH:
        if retry_count < malformed_retry_budget:
            return RecoveryDecision(
                action=RecoveryAction.RETRY_WITH_SCHEMA_REMINDER,
                failure_class=FailureClass.TRANSIENT,
                error_code=error_code,
                reason=(
                    f"output-shape error {error_code.value}; retry "
                    f"{retry_count + 1}/{malformed_retry_budget} with "
                    f"schema reminder injected into prompt"
                ),
            )
        return RecoveryDecision(
            action=RecoveryAction.BLOCK_EXECUTION,
            failure_class=FailureClass.TRANSIENT,
            error_code=error_code,
            reason=(
                f"output-shape retry budget exhausted "
                f"({retry_count}/{malformed_retry_budget})"
            ),
        )

    # Provider/network transient
    if error_code in (ErrorCode.PROVIDER_5XX, ErrorCode.NETWORK_TIMEOUT, ErrorCode.RATE_LIMITED):
        if retry_count < transient_retry_budget:
            # Provider/rate-limit transient: try same prompt first; if
            # caller has fallback chain available (L3.4) they may swap
            # model on next retry — that's caller's choice.
            return RecoveryDecision(
                action=RecoveryAction.RETRY_SAME_PROMPT,
                failure_class=FailureClass.TRANSIENT,
                error_code=error_code,
                reason=(
                    f"transient {error_code.value}; retry "
                    f"{retry_count + 1}/{transient_retry_budget} same prompt"
                ),
            )
        return RecoveryDecision(
            action=RecoveryAction.FALLBACK_MODEL,
            failure_class=FailureClass.TRANSIENT,
            error_code=error_code,
            reason=(
                f"transient {error_code.value} budget exhausted "
                f"({retry_count}/{transient_retry_budget}); fallback to "
                f"next model in chain"
            ),
        )

    # Defensive: unknown transient -> BLOCK (shouldn't reach here given
    # the closed _TRANSIENT_CODES set, but fail-safe).
    return RecoveryDecision(
        action=RecoveryAction.BLOCK_EXECUTION,
        failure_class=FailureClass.TRANSIENT,
        error_code=error_code,
        reason="unhandled transient code; BLOCKED defensively",
    )
