"""OpenTelemetry tracing — distributed trace instrumentation.

Decision #2 A: opt-in via `FORGE_OTEL_ENABLED=true` env. Deps are
installed unconditionally (see pyproject.toml) so flipping the flag
is a one-line operator change, not a dep rebuild.

Env contract:
  FORGE_OTEL_ENABLED          — "true" to turn on (default: off)
  FORGE_OTEL_SERVICE_NAME     — default "forge-platform"
  FORGE_OTEL_EXPORTER         — "otlp" (default) | "console" (debug)
  OTEL_EXPORTER_OTLP_ENDPOINT — standard OTel env; set by operator
                                for OTLP receiver (e.g. Tempo, Jaeger,
                                Datadog APM, Honeycomb)

What instruments:
  - FastAPI: auto-spans for every HTTP request with route template
  - SQLAlchemy: auto-spans for every DB query

What does NOT auto-instrument (intentional):
  - `httpx` client calls (Claude CLI subprocess, GitHub PR) — these
    are subprocess/process-out so OTel context propagation needs
    explicit effort; add if/when user needs external-call visibility
  - Background task worker (N+1 profiler already covers DB-side)

Design: setup is idempotent. Calling `setup_tracing()` twice doesn't
double-register. Matches `configure_logging()` pattern so multi-
worker deploys (uvicorn --workers N) don't explode.
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_INSTALLED = False
_INSTALL_LOCK = threading.Lock()


def _enabled() -> bool:
    return os.environ.get("FORGE_OTEL_ENABLED", "").lower() in ("1", "true", "yes")


def _service_name() -> str:
    return os.environ.get("FORGE_OTEL_SERVICE_NAME", "forge-platform")


def _exporter_choice() -> str:
    return os.environ.get("FORGE_OTEL_EXPORTER", "otlp").lower()


def setup_tracing(app=None, engine=None) -> bool:
    """Configure the global tracer provider + auto-instrument FastAPI + SQLAlchemy.

    app:    optional FastAPI instance (for FastAPI instrumentation)
    engine: optional SQLAlchemy engine (for DB instrumentation)

    Returns True if tracing was enabled and set up; False if disabled
    (FORGE_OTEL_ENABLED not set) or if setup failed (logged; not raised).

    Idempotent: subsequent calls are no-ops.
    """
    global _INSTALLED

    if not _enabled():
        return False

    with _INSTALL_LOCK:
        if _INSTALLED:
            return True
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

            resource = Resource.create({"service.name": _service_name()})
            provider = TracerProvider(resource=resource)

            # Choose exporter
            choice = _exporter_choice()
            if choice == "console":
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            else:  # "otlp" default — relies on standard OTel env for endpoint
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

            trace.set_tracer_provider(provider)

            # Auto-instrument FastAPI
            if app is not None:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app)

            # Auto-instrument SQLAlchemy
            if engine is not None:
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
                SQLAlchemyInstrumentor().instrument(engine=engine)

            _INSTALLED = True
            logger.info(
                "otel: tracing enabled, service=%s, exporter=%s",
                _service_name(), choice,
            )
            return True
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("otel: setup failed: %s — tracing remains disabled", e)
            return False


def is_enabled() -> bool:
    """True once setup_tracing has succeeded in this process."""
    return _INSTALLED


def get_tracer(name: str = "forge"):
    """Return a tracer for creating custom spans in handler code.

    Always returns a tracer object — when tracing is disabled, it's a
    no-op tracer (spans created are free). Lets handlers use
    `with tracer.start_as_current_span("...")` unconditionally.
    """
    from opentelemetry import trace
    return trace.get_tracer(name)
