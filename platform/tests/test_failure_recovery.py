"""Tests for FailureRecovery — Phase L3 Stage L3.5.

Pure rule-based tests: same (error_code, retry_count, budgets) ->
same RecoveryDecision. No LLM-in-loop.
"""

from __future__ import annotations

from app.llm.failure_recovery import (
    DEFAULT_MALFORMED_RETRY_BUDGET,
    DEFAULT_TRANSIENT_RETRY_BUDGET,
    ErrorCode,
    FailureClass,
    RecoveryAction,
    RecoveryDecision,
    classify,
    decide,
)


# --- classify() ----------------------------------------------------------


def test_provider_5xx_is_transient():
    assert classify(ErrorCode.PROVIDER_5XX) == FailureClass.TRANSIENT


def test_network_timeout_is_transient():
    assert classify(ErrorCode.NETWORK_TIMEOUT) == FailureClass.TRANSIENT


def test_rate_limited_is_transient():
    assert classify(ErrorCode.RATE_LIMITED) == FailureClass.TRANSIENT


def test_json_parse_error_is_transient():
    assert classify(ErrorCode.JSON_PARSE_ERROR) == FailureClass.TRANSIENT


def test_schema_mismatch_is_transient():
    assert classify(ErrorCode.SCHEMA_MISMATCH) == FailureClass.TRANSIENT


def test_auth_failure_is_permanent():
    assert classify(ErrorCode.AUTH_FAILURE) == FailureClass.PERMANENT


def test_model_deprecated_is_permanent():
    assert classify(ErrorCode.MODEL_DEPRECATED) == FailureClass.PERMANENT


def test_budget_exceeded_is_permanent():
    assert classify(ErrorCode.BUDGET_EXCEEDED) == FailureClass.PERMANENT


def test_all_models_unavailable_is_permanent():
    assert classify(ErrorCode.ALL_MODELS_UNAVAILABLE) == FailureClass.PERMANENT


def test_unknown_is_permanent_failsafe():
    """Unknown errors default to PERMANENT — fail-safe per CONTRACT §B.2."""
    assert classify(ErrorCode.UNKNOWN) == FailureClass.PERMANENT


# --- decide() — permanent failures always BLOCK -------------------------


def test_auth_failure_blocks_immediately():
    d = decide(ErrorCode.AUTH_FAILURE, retry_count=0)
    assert d.action == RecoveryAction.BLOCK_EXECUTION
    assert d.failure_class == FailureClass.PERMANENT
    assert "auth_failure" in d.reason


def test_budget_exceeded_blocks():
    d = decide(ErrorCode.BUDGET_EXCEEDED, retry_count=0)
    assert d.action == RecoveryAction.BLOCK_EXECUTION


def test_unknown_blocks():
    d = decide(ErrorCode.UNKNOWN, retry_count=0)
    assert d.action == RecoveryAction.BLOCK_EXECUTION
    assert d.failure_class == FailureClass.PERMANENT


# --- decide() — transient retry behaviour --------------------------------


def test_provider_5xx_first_failure_retries_same_prompt():
    d = decide(ErrorCode.PROVIDER_5XX, retry_count=0)
    assert d.action == RecoveryAction.RETRY_SAME_PROMPT
    assert d.failure_class == FailureClass.TRANSIENT
    assert "1/1" in d.reason


def test_provider_5xx_after_budget_falls_back_to_next_model():
    """retry_count >= budget -> FALLBACK_MODEL (next in L3.4 chain)."""
    d = decide(ErrorCode.PROVIDER_5XX, retry_count=DEFAULT_TRANSIENT_RETRY_BUDGET)
    assert d.action == RecoveryAction.FALLBACK_MODEL
    assert "fallback" in d.reason


def test_network_timeout_uses_same_transient_budget():
    d = decide(ErrorCode.NETWORK_TIMEOUT, retry_count=0)
    assert d.action == RecoveryAction.RETRY_SAME_PROMPT


def test_rate_limited_uses_transient_budget():
    d = decide(ErrorCode.RATE_LIMITED, retry_count=0)
    assert d.action == RecoveryAction.RETRY_SAME_PROMPT


# --- decide() — output-shape errors get schema-reminder retry ------------


def test_json_parse_error_first_retries_with_schema_reminder():
    d = decide(ErrorCode.JSON_PARSE_ERROR, retry_count=0)
    assert d.action == RecoveryAction.RETRY_WITH_SCHEMA_REMINDER
    assert d.failure_class == FailureClass.TRANSIENT
    assert "schema reminder" in d.reason


def test_schema_mismatch_first_retries_with_schema_reminder():
    d = decide(ErrorCode.SCHEMA_MISMATCH, retry_count=0)
    assert d.action == RecoveryAction.RETRY_WITH_SCHEMA_REMINDER


def test_json_parse_error_within_malformed_budget_retries():
    """retry_count < malformed_retry_budget -> still retry."""
    d = decide(
        ErrorCode.JSON_PARSE_ERROR,
        retry_count=DEFAULT_MALFORMED_RETRY_BUDGET - 1,
    )
    assert d.action == RecoveryAction.RETRY_WITH_SCHEMA_REMINDER


def test_json_parse_error_after_malformed_budget_blocks():
    """retry_count >= budget -> BLOCK_EXECUTION (no infinite retries)."""
    d = decide(
        ErrorCode.JSON_PARSE_ERROR,
        retry_count=DEFAULT_MALFORMED_RETRY_BUDGET,
    )
    assert d.action == RecoveryAction.BLOCK_EXECUTION
    assert "exhausted" in d.reason


def test_schema_mismatch_after_budget_blocks():
    d = decide(
        ErrorCode.SCHEMA_MISMATCH,
        retry_count=DEFAULT_MALFORMED_RETRY_BUDGET,
    )
    assert d.action == RecoveryAction.BLOCK_EXECUTION


# --- Custom budgets ------------------------------------------------------


def test_custom_transient_budget_respected():
    """Higher budget -> retry possible at higher retry_count."""
    d = decide(ErrorCode.PROVIDER_5XX, retry_count=2, transient_retry_budget=5)
    assert d.action == RecoveryAction.RETRY_SAME_PROMPT


def test_custom_malformed_budget_zero_blocks_first_retry():
    """malformed_retry_budget=0 -> first failure already exceeds budget -> BLOCK."""
    d = decide(ErrorCode.JSON_PARSE_ERROR, retry_count=0, malformed_retry_budget=0)
    assert d.action == RecoveryAction.BLOCK_EXECUTION


# --- Determinism (P6) ----------------------------------------------------


def test_decide_determinism():
    """Same arguments -> same RecoveryDecision."""
    args = (ErrorCode.PROVIDER_5XX,)
    kwargs = {"retry_count": 0}
    d1 = decide(*args, **kwargs)
    d2 = decide(*args, **kwargs)
    d3 = decide(*args, **kwargs)
    assert d1 == d2 == d3


def test_recovery_decision_is_frozen_dataclass():
    d = decide(ErrorCode.AUTH_FAILURE, retry_count=0)
    try:
        d.action = RecoveryAction.RETRY_SAME_PROMPT  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("RecoveryDecision should be frozen")


# --- Acceptance: every ErrorCode produces a defined decision -------------


def test_every_error_code_has_a_decision():
    """Coverage check: classify() + decide() handle every enum value."""
    for code in ErrorCode:
        cls = classify(code)
        d = decide(code, retry_count=0)
        assert isinstance(d, RecoveryDecision)
        assert d.failure_class == cls
        assert d.error_code == code
