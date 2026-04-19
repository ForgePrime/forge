"""Query profiler — detects N+1 patterns during request handling.

Zero new dependencies: wires into SQLAlchemy's existing event system.

Usage modes:
  - Middleware (preferred) — wraps each request, reports N+1 via log/header
  - Context manager — scope profiling to a specific code block in tests
  - Ad-hoc via `start()` / `stop()` for one-off inspection

What counts as N+1:
  The same SQL statement (normalized — parameter placeholders collapsed)
  executed >= `N_PLUS_ONE_THRESHOLD` times during the same request/context.
  Default threshold: 5. Tune via `FORGE_NPLUS1_THRESHOLD` env.

Output:
  Each breach produces a structured log record at WARNING level with:
    - normalized_statement     (first 400 chars, parameter-free)
    - count                    (how many times it ran)
    - request_id               (from logging contextvar if available)
    - caller_hint              (first non-sqlalchemy stack frame)

No blocking. Profiler is diagnostic — reports, never raises.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
import os
import re
import threading
import traceback
from collections import defaultdict

from sqlalchemy import event

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 5


def _threshold() -> int:
    try:
        return int(os.environ.get("FORGE_NPLUS1_THRESHOLD", _DEFAULT_THRESHOLD))
    except ValueError:
        return _DEFAULT_THRESHOLD


# Per-scope statement counter. Context var → request-scoped isolation.
_scope_counter: contextvars.ContextVar[dict[str, int] | None] = contextvars.ContextVar(
    "forge_query_profiler_scope", default=None,
)

# Normalizing regex — collapses parameter placeholders + whitespace.
_PLACEHOLDER_RE = re.compile(r"%\([a-zA-Z0-9_]+\)s|\$\d+|\?")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(stmt: str) -> str:
    if not stmt:
        return ""
    out = _PLACEHOLDER_RE.sub("?", stmt)
    out = _WHITESPACE_RE.sub(" ", out).strip()
    return out[:400]


def _caller_hint() -> str:
    """First stack frame that isn't in sqlalchemy/ or this module."""
    try:
        for frame in traceback.extract_stack()[::-1]:
            fn = frame.filename or ""
            if "sqlalchemy" in fn or "query_profiler" in fn:
                continue
            if fn.endswith((".py",)):
                return f"{fn.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]}:{frame.lineno} {frame.name}"
    except Exception:
        pass
    return "<caller unknown>"


def _after_execute(conn, cursor, statement, parameters, context, executemany):
    """SQLAlchemy `after_cursor_execute` listener."""
    counter = _scope_counter.get()
    if counter is None:
        return
    norm = _normalize(statement)
    counter[norm] = counter.get(norm, 0) + 1


# Event is wired lazily to avoid side effects at import.
_WIRED = False
_WIRED_LOCK = threading.Lock()


def ensure_wired(engine) -> None:
    """Install the event listener on the given engine. Idempotent."""
    global _WIRED
    with _WIRED_LOCK:
        if _WIRED:
            return
        event.listen(engine, "after_cursor_execute", _after_execute)
        _WIRED = True


@contextlib.contextmanager
def scope(name: str = "scope"):
    """Context-managed profiling scope.

    Usage:
        from app.database import engine
        from app.services.query_profiler import ensure_wired, scope
        ensure_wired(engine)
        with scope("my_handler") as s:
            ...  # code that hits DB
        # s.breaches: list of (normalized_stmt, count) for threshold violators
    """
    token = _scope_counter.set({})
    result = _ScopeResult(name=name)
    try:
        yield result
    finally:
        counter = _scope_counter.get() or {}
        result.finalize(counter)
        _scope_counter.reset(token)


class _ScopeResult:
    def __init__(self, name: str):
        self.name = name
        self.counts: dict[str, int] = {}
        self.breaches: list[tuple[str, int]] = []
        self.total_statements: int = 0

    def finalize(self, counter: dict[str, int]) -> None:
        self.counts = dict(counter)
        self.total_statements = sum(counter.values())
        thresh = _threshold()
        self.breaches = [(s, c) for s, c in counter.items() if c >= thresh]

    def log_breaches(self, extra_context: dict | None = None) -> None:
        """Emit WARNING logs for each breach. Useful from middleware."""
        if not self.breaches:
            return
        ctx = extra_context or {}
        for stmt, count in self.breaches:
            logger.warning(
                "n+1 detected: same statement ran %d× in scope=%s",
                count, self.name,
                extra={
                    "normalized_statement": stmt,
                    "count": count,
                    "scope_name": self.name,
                    **ctx,
                },
            )


def report_scope(name: str, counter: dict[str, int]) -> _ScopeResult:
    """Build a result from an already-finished scope's counter (for tests)."""
    r = _ScopeResult(name=name)
    r.finalize(counter)
    return r
