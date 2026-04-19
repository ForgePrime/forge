"""Prometheus metrics — counters + histograms + gauges.

Wired into `/metrics` endpoint (public, scraped by Prometheus/Datadog).
Counters accumulate, histograms bucket, gauges reflect instantaneous state.

Naming: `forge_<domain>_<metric>_<unit>` (Prometheus convention).
Labels kept LOW cardinality (never user_id or task_id — those explode series).

Metrics exposed:
  forge_http_requests_total{method, route, status}
    Counter — every HTTP request. `route` is the route pattern
    (e.g. "/api/v1/projects/{slug}/ingest"), not the expanded path, so
    cardinality stays bounded even with many project slugs.

  forge_http_request_duration_seconds{method, route}
    Histogram — request latency. Buckets tuned for web app (10ms to 10s).

  forge_llm_calls_total{purpose, model}
    Counter — every LLM call. `purpose` is execute/crafter/challenge/etc.

  forge_llm_cost_usd_total{purpose, model}
    Counter — cumulative $ spent. Used for SLO-4 cost per task tracking.

  forge_orchestrate_runs_total{status}
    Counter — PENDING/RUNNING/DONE/FAILED/INTERRUPTED transitions.

  forge_task_status{status}
    Gauge — current count of tasks in each status (TODO/IN_PROGRESS/DONE/...).
    Useful for "stuck task" alerting.

Tests validate metric names + label cardinality + counter monotonicity.
"""
from __future__ import annotations

from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST,
)


# Use the default global registry — prometheus_client's singleton. One
# process = one registry. Multi-worker deployments (uvicorn --workers N)
# need multiprocess mode; see docs/WIRING_GUIDE.md for the prod recipe.

http_requests_total = Counter(
    "forge_http_requests_total",
    "Total HTTP requests handled by Forge",
    ["method", "route", "status"],
)

http_request_duration_seconds = Histogram(
    "forge_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)

llm_calls_total = Counter(
    "forge_llm_calls_total",
    "Total LLM invocations",
    ["purpose", "model"],
)

llm_cost_usd_total = Counter(
    "forge_llm_cost_usd_total",
    "Cumulative USD spent on LLM calls",
    ["purpose", "model"],
)

orchestrate_runs_total = Counter(
    "forge_orchestrate_runs_total",
    "Orchestrate run lifecycle events (one increment per status transition)",
    ["status"],
)

task_status_gauge = Gauge(
    "forge_task_status",
    "Current count of tasks in each status (instantaneous)",
    ["status"],
)


# ---------- Helpers that handlers can call ----------

def record_llm_call(purpose: str, model: str, cost_usd: float | None) -> None:
    """Public helper: records one LLM call + its cost.

    Handlers call this after saving an LLMCall row. Protects metric
    code from label-explosion by clipping purpose/model to known-finite
    sets; unknowns are labelled 'other'.
    """
    safe_purpose = purpose if purpose in {
        "execute", "crafter", "challenge", "analyze", "plan", "extract",
    } else "other"
    safe_model = (model or "unknown")[:80]
    llm_calls_total.labels(purpose=safe_purpose, model=safe_model).inc()
    if cost_usd is not None:
        try:
            llm_cost_usd_total.labels(purpose=safe_purpose, model=safe_model).inc(float(cost_usd))
        except (TypeError, ValueError):
            pass


def record_orchestrate_transition(status: str) -> None:
    """Public helper: records an orchestrate run entering `status`."""
    safe_status = status if status in {
        "PENDING", "RUNNING", "PAUSED", "DONE", "FAILED",
        "CANCELLED", "BUDGET_EXCEEDED", "PARTIAL_FAIL", "INTERRUPTED",
    } else "other"
    orchestrate_runs_total.labels(status=safe_status).inc()


def render_metrics() -> tuple[bytes, str]:
    """Return (payload, content_type) for a Prometheus scrape response."""
    return generate_latest(), CONTENT_TYPE_LATEST


# ---------- Middleware ----------

import time as _time
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    """Per-request HTTP counters + latency histogram.

    Label policy:
      - `route` = route template from Starlette (e.g. "/api/v1/projects/{slug}/ingest")
        NOT the expanded path — keeps cardinality bounded.
      - `method` = HTTP verb.
      - `status` = response status code.

    If route can't be extracted (e.g. 404), labelled as "unknown" to
    avoid series explosion on crawler 404s.
    """

    async def dispatch(self, request, call_next):
        start = _time.monotonic()
        method = request.method
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            # Count the exception path but re-raise — other error handlers
            # deal with the response.
            status = 500
            try:
                route = request.scope.get("route")
                route_path = route.path if route else "unknown"
            except Exception:
                route_path = "unknown"
            http_requests_total.labels(method=method, route=route_path, status=str(status)).inc()
            http_request_duration_seconds.labels(method=method, route=route_path).observe(
                _time.monotonic() - start
            )
            raise

        # Extract route template — bounded cardinality
        try:
            route = request.scope.get("route")
            route_path = route.path if route else "unknown"
        except Exception:
            route_path = "unknown"

        http_requests_total.labels(method=method, route=route_path, status=str(status)).inc()
        http_request_duration_seconds.labels(method=method, route=route_path).observe(
            _time.monotonic() - start
        )
        return response
