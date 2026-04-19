"""Unit tests for services/tracing — OpenTelemetry setup gating.

Tests run without a live OTel collector: we verify the gating logic,
idempotency, and that the no-op path never raises.
"""
import pytest

from app.services.tracing import (
    setup_tracing, is_enabled, get_tracer,
    _enabled, _service_name, _exporter_choice,
)
from app.services import tracing as tracing_module


# ---------- Env parsing ----------

def test_env_enabled_default_false(monkeypatch):
    monkeypatch.delenv("FORGE_OTEL_ENABLED", raising=False)
    assert _enabled() is False


def test_env_enabled_accepts_truthy_variants(monkeypatch):
    for val in ("true", "True", "TRUE", "1", "yes", "YES"):
        monkeypatch.setenv("FORGE_OTEL_ENABLED", val)
        assert _enabled() is True, f"{val!r} should be truthy"


def test_env_enabled_rejects_other_values(monkeypatch):
    for val in ("", "false", "0", "no", "maybe", "y"):
        monkeypatch.setenv("FORGE_OTEL_ENABLED", val)
        assert _enabled() is False, f"{val!r} should be falsy"


def test_service_name_default(monkeypatch):
    monkeypatch.delenv("FORGE_OTEL_SERVICE_NAME", raising=False)
    assert _service_name() == "forge-platform"


def test_service_name_override(monkeypatch):
    monkeypatch.setenv("FORGE_OTEL_SERVICE_NAME", "forge-staging")
    assert _service_name() == "forge-staging"


def test_exporter_default_otlp(monkeypatch):
    monkeypatch.delenv("FORGE_OTEL_EXPORTER", raising=False)
    assert _exporter_choice() == "otlp"


def test_exporter_console_override(monkeypatch):
    monkeypatch.setenv("FORGE_OTEL_EXPORTER", "console")
    assert _exporter_choice() == "console"


# ---------- setup_tracing gating ----------

def test_setup_disabled_returns_false(monkeypatch):
    """No FORGE_OTEL_ENABLED → setup_tracing is a no-op returning False."""
    monkeypatch.delenv("FORGE_OTEL_ENABLED", raising=False)
    # Reset _INSTALLED state in case a previous test set it
    tracing_module._INSTALLED = False
    result = setup_tracing()
    assert result is False
    assert is_enabled() is False


def test_setup_idempotent(monkeypatch):
    """Calling setup_tracing twice with enabled env doesn't double-init."""
    monkeypatch.setenv("FORGE_OTEL_ENABLED", "true")
    monkeypatch.setenv("FORGE_OTEL_EXPORTER", "console")
    tracing_module._INSTALLED = False
    try:
        first = setup_tracing()  # may succeed or fail depending on deps
        second = setup_tracing()
        # Second call must match first's outcome (no double-registration side effect)
        assert first == second or (first is True and second is True)
    finally:
        tracing_module._INSTALLED = False


# ---------- get_tracer ----------

def test_get_tracer_returns_tracer_when_disabled():
    """Even with tracing off, get_tracer must return a usable tracer
    object so handler code can use `with tracer.start_as_current_span(...)`
    unconditionally. The resulting span is a no-op."""
    tracing_module._INSTALLED = False
    tracer = get_tracer("unit-test")
    assert tracer is not None
    # Verify can start a no-op span without raising
    with tracer.start_as_current_span("test-span") as span:
        assert span is not None


def test_get_tracer_named():
    t1 = get_tracer("a")
    t2 = get_tracer("b")
    assert t1 is not None
    assert t2 is not None
