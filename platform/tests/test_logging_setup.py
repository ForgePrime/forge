"""Unit tests for services/logging_setup — JSON formatter + request-id middleware."""
import io
import json
import logging
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.logging_setup import (
    JsonFormatter, RequestIdFilter, configure_logging, RequestIdMiddleware,
    current_request_id, _request_id_var,
)


# ---------- JsonFormatter ----------

def test_json_formatter_basic_shape():
    rec = logging.LogRecord(
        name="app.test", level=logging.INFO, pathname=__file__, lineno=10,
        msg="hello %s", args=("world",), exc_info=None,
    )
    rec.request_id = "req-123"
    out = JsonFormatter().format(rec)
    obj = json.loads(out)
    assert obj["level"] == "INFO"
    assert obj["logger"] == "app.test"
    assert obj["msg"] == "hello world"
    assert obj["request_id"] == "req-123"
    assert "ts" in obj


def test_json_formatter_single_line():
    """Every record must serialize to ONE line (log shipping invariant)."""
    rec = logging.LogRecord(
        name="a", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="multi\nline\nmessage", args=None, exc_info=None,
    )
    rec.request_id = "-"
    out = JsonFormatter().format(rec)
    assert "\n" not in out
    parsed = json.loads(out)
    assert "multi\nline\nmessage" in parsed["msg"]


def test_json_formatter_captures_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        rec = logging.LogRecord(
            name="a", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="error path", args=None, exc_info=sys.exc_info(),
        )
    rec.request_id = "-"
    out = JsonFormatter().format(rec)
    obj = json.loads(out)
    assert "exc" in obj
    assert "ValueError" in obj["exc"]
    assert "boom" in obj["exc"]


def test_json_formatter_extras_included():
    rec = logging.LogRecord(
        name="a", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello", args=None, exc_info=None,
    )
    rec.request_id = "-"
    rec.user_id = 42
    rec.project_slug = "acme"
    out = JsonFormatter().format(rec)
    obj = json.loads(out)
    assert obj["extra"]["user_id"] == 42
    assert obj["extra"]["project_slug"] == "acme"


def test_json_formatter_non_serializable_extras_fallback():
    """Non-JSON-serializable extras should not crash — coerce via str()."""
    class Weird:
        def __repr__(self):
            return "<weird>"

    rec = logging.LogRecord(
        name="a", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello", args=None, exc_info=None,
    )
    rec.request_id = "-"
    rec.weird_obj = Weird()
    out = JsonFormatter().format(rec)
    obj = json.loads(out)
    # Either the extras dict exists with string-coerced value or JSON lib
    # accepted it via default=str. Both paths keep the pipeline alive.
    assert "extra" in obj


# ---------- RequestIdFilter ----------

def test_filter_injects_default_dash_outside_request():
    f = RequestIdFilter()
    rec = logging.LogRecord(
        name="a", level=logging.INFO, pathname=__file__, lineno=1,
        msg="x", args=None, exc_info=None,
    )
    # Clear any leaked contextvar state
    token = _request_id_var.set("-")
    try:
        f.filter(rec)
        assert rec.request_id == "-"
    finally:
        _request_id_var.reset(token)


def test_filter_injects_current_id():
    f = RequestIdFilter()
    token = _request_id_var.set("abc123")
    try:
        rec = logging.LogRecord(
            name="a", level=logging.INFO, pathname=__file__, lineno=1,
            msg="x", args=None, exc_info=None,
        )
        f.filter(rec)
        assert rec.request_id == "abc123"
    finally:
        _request_id_var.reset(token)


# ---------- configure_logging opt-in ----------

def test_configure_logging_stdlib_by_default(monkeypatch):
    """Without env var → stdlib formatter (readable text)."""
    monkeypatch.delenv("FORGE_LOG_JSON", raising=False)
    configure_logging(force_json=False, level="INFO")
    root = logging.getLogger()
    assert root.handlers
    fmt = root.handlers[0].formatter
    assert not isinstance(fmt, JsonFormatter)


def test_configure_logging_json_when_forced():
    configure_logging(force_json=True, level="DEBUG")
    root = logging.getLogger()
    fmt = root.handlers[0].formatter
    assert isinstance(fmt, JsonFormatter)
    # Reset to default for other tests
    configure_logging(force_json=False, level="INFO")


def test_configure_logging_is_idempotent():
    """Calling configure_logging N times must not stack N handlers."""
    configure_logging(force_json=False, level="INFO")
    configure_logging(force_json=False, level="INFO")
    configure_logging(force_json=False, level="INFO")
    root = logging.getLogger()
    assert len(root.handlers) == 1


# ---------- RequestIdMiddleware integration ----------

def _make_app():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/echo")
    def echo():
        # Within a request, current_request_id() should return non-default
        return {"rid": current_request_id()}

    return app


def test_middleware_assigns_uuid_when_no_header():
    client = TestClient(_make_app())
    r = client.get("/echo")
    assert r.status_code == 200
    rid = r.json()["rid"]
    assert rid != "-"
    assert len(rid) >= 16  # uuid4().hex is 32
    # Echoed back to client
    assert r.headers["X-Request-Id"] == rid


def test_middleware_honors_client_supplied_request_id():
    client = TestClient(_make_app())
    r = client.get("/echo", headers={"X-Request-Id": "client-trace-42"})
    assert r.json()["rid"] == "client-trace-42"
    assert r.headers["X-Request-Id"] == "client-trace-42"


def test_middleware_request_id_isolated_across_requests():
    """Two sequential requests must get different IDs when client doesn't supply."""
    client = TestClient(_make_app())
    r1 = client.get("/echo")
    r2 = client.get("/echo")
    assert r1.json()["rid"] != r2.json()["rid"]


def test_current_request_id_outside_request_returns_dash():
    # Outside any request context — contextvar default
    token = _request_id_var.set("-")
    try:
        assert current_request_id() == "-"
    finally:
        _request_id_var.reset(token)
