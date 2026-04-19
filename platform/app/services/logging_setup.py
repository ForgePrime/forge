"""JSON structured logging for production — stdlib only, zero new deps.

Opt-in via env var `FORGE_LOG_JSON=true`. When unset (default) Python's
stdlib logging is used unchanged, so local dev and tests remain readable.

In JSON mode, every log line is a single-line JSON object:

    {"ts":"2026-04-19T10:00:00Z","level":"INFO","logger":"app.api.pipeline",
     "msg":"...","request_id":"<uuid>","extra":{...}}

A small middleware assigns a request_id per HTTP request and sets it in a
contextvar so downstream log calls pick it up automatically. The field is
also echoed back to the client as `X-Request-Id` response header so logs
and client-side incident reports can be correlated.

Why not structlog / loguru?
  - Zero-dep is a hard requirement for this autonomous session — adding a
    dep requires user approval.
  - stdlib logging is already used in 4+ modules (main.py, hooks_runner.py,
    orphan_recovery.py, schema_migrations.py). Replacing it globally would
    be a larger change; adding a JSON formatter on top is additive.
  - If needs grow beyond what stdlib provides (bound loggers, processors),
    migrate to structlog in a dedicated session with user go-ahead.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


# ---- Context variable populated by middleware, read by filter ----

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "forge_request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Inject current request_id into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON.

    Includes: ts (ISO-8601 UTC), level, logger, msg, request_id, extra fields.
    Exception info (if any) becomes a string field under "exc".
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base payload — always present
        payload = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        # Exception info — stringify once
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # stackinfo (rare)
        if getattr(record, "stack_info", None):
            payload["stack"] = self.formatStack(record.stack_info)

        # Custom extras (caller passed extra={...}) — pick everything that
        # isn't a stdlib LogRecord attribute.
        _std = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "request_id",
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in _std}
        if extras:
            # Non-serializable values → str() fallback
            try:
                payload["extra"] = extras
                json.dumps(payload)  # dry run
            except TypeError:
                payload["extra"] = {k: str(v) for k, v in extras.items()}

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(*, force_json: bool | None = None, level: str | None = None) -> None:
    """Configure root logger.

    Honored env vars:
      FORGE_LOG_JSON=true|1|yes → JSON formatter (default: stdlib)
      FORGE_LOG_LEVEL=DEBUG|INFO|... (default: INFO)

    Idempotent — safe to call multiple times (replaces existing handlers).
    """
    if force_json is None:
        force_json = os.environ.get("FORGE_LOG_JSON", "").lower() in ("1", "true", "yes")
    if level is None:
        level = os.environ.get("FORGE_LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    # Clear any prior handlers so re-configuration is clean
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if force_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s request_id=%(request_id)s — %(message)s"
        ))

    root.addHandler(handler)
    root.setLevel(level)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request_id per request, echo back as `X-Request-Id` header.

    Accepts a client-supplied `X-Request-Id` for end-to-end tracing from a
    gateway; otherwise generates a UUID4.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id")
        rid = incoming if incoming else uuid.uuid4().hex
        token = _request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers["X-Request-Id"] = rid
        return response


def current_request_id() -> str:
    """Exposed helper for non-logging callers who want to include the ID elsewhere
    (e.g., inserting into an audit row). Returns '-' outside a request context.
    """
    return _request_id_var.get()
