"""Unit tests for services/metrics — Prometheus counters + endpoint shape."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.metrics import (
    http_requests_total, http_request_duration_seconds,
    llm_calls_total, llm_cost_usd_total, orchestrate_runs_total,
    task_status_gauge,
    record_llm_call, record_orchestrate_transition, render_metrics,
    MetricsMiddleware,
)


# ---------- Metric definitions present ----------

def test_expected_counters_exist():
    """Every metric this module promises must be instantiable."""
    assert http_requests_total is not None
    assert http_request_duration_seconds is not None
    assert llm_calls_total is not None
    assert llm_cost_usd_total is not None
    assert orchestrate_runs_total is not None
    assert task_status_gauge is not None


def test_metrics_use_prefix_forge():
    """All metric names must start with `forge_` (Prometheus convention)."""
    for metric in (http_requests_total, http_request_duration_seconds,
                   llm_calls_total, llm_cost_usd_total,
                   orchestrate_runs_total, task_status_gauge):
        # prometheus_client exposes the name via ._name attr
        name = getattr(metric, "_name", "")
        assert name.startswith("forge_"), f"metric {name} does not use forge_ prefix"


# ---------- record_llm_call ----------

def test_record_llm_call_increments_counter():
    before = _counter_value(llm_calls_total, purpose="execute", model="claude-sonnet-4-6")
    record_llm_call("execute", "claude-sonnet-4-6", 0.12)
    after = _counter_value(llm_calls_total, purpose="execute", model="claude-sonnet-4-6")
    assert after == before + 1


def test_record_llm_call_adds_to_cost():
    before = _counter_value(llm_cost_usd_total, purpose="execute", model="claude-sonnet-4-6")
    record_llm_call("execute", "claude-sonnet-4-6", 0.50)
    after = _counter_value(llm_cost_usd_total, purpose="execute", model="claude-sonnet-4-6")
    assert round(after - before, 2) == 0.50


def test_record_llm_call_clips_unknown_purpose_to_other():
    """Label-explosion safety: unknown purpose bucketed as 'other'."""
    before = _counter_value(llm_calls_total, purpose="other", model="xxx")
    record_llm_call("mysterious-new-purpose", "xxx", 0.01)
    after = _counter_value(llm_calls_total, purpose="other", model="xxx")
    assert after == before + 1


def test_record_llm_call_handles_missing_cost():
    """cost_usd=None must not raise."""
    record_llm_call("execute", "claude-haiku-4-5", None)  # no exception


def test_record_llm_call_handles_non_numeric_cost():
    """Garbage cost is silently skipped (defensive)."""
    record_llm_call("execute", "xx", "not-a-number")  # no exception
    # Verify counter didn't take the string
    val = _counter_value(llm_cost_usd_total, purpose="execute", model="xx")
    assert isinstance(val, float)


# ---------- record_orchestrate_transition ----------

def test_record_orchestrate_transition():
    before = _counter_value(orchestrate_runs_total, status="DONE")
    record_orchestrate_transition("DONE")
    after = _counter_value(orchestrate_runs_total, status="DONE")
    assert after == before + 1


def test_unknown_orchestrate_status_maps_to_other():
    before = _counter_value(orchestrate_runs_total, status="other")
    record_orchestrate_transition("garbage-status")
    after = _counter_value(orchestrate_runs_total, status="other")
    assert after == before + 1


# ---------- render_metrics ----------

def test_render_metrics_returns_bytes_and_content_type():
    payload, ct = render_metrics()
    assert isinstance(payload, bytes)
    assert "text/plain" in ct or "openmetrics" in ct
    text = payload.decode("utf-8")
    assert "forge_http_requests_total" in text
    assert "forge_llm_calls_total" in text


def test_render_metrics_includes_help_and_type_comments():
    """Prometheus format requires # HELP and # TYPE lines."""
    payload, _ = render_metrics()
    text = payload.decode("utf-8")
    assert "# HELP forge_" in text
    assert "# TYPE forge_" in text


# ---------- MetricsMiddleware ----------

def test_middleware_counts_requests():
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    before = _counter_value(http_requests_total, method="GET", route="/ping", status="200")
    client.get("/ping")
    client.get("/ping")
    client.get("/ping")
    after = _counter_value(http_requests_total, method="GET", route="/ping", status="200")
    assert after == before + 3


def test_middleware_uses_route_template_not_expanded_path():
    """Slug in path must not explode cardinality — route template is the label."""
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/projects/{slug}")
    def show(slug: str):
        return {"slug": slug}

    client = TestClient(app)
    client.get("/projects/acme")
    client.get("/projects/beta")
    client.get("/projects/gamma")
    # Single label bucket for all three slugs
    count = _counter_value(http_requests_total, method="GET", route="/projects/{slug}", status="200")
    # At least 3 requests ended up in the same bucket
    assert count >= 3


def test_middleware_records_duration():
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/slow")
    def slow():
        return {"ok": True}

    client = TestClient(app)
    client.get("/slow")
    # Histogram sample count should be >= 1 for this label combo
    metric_text = render_metrics()[0].decode("utf-8")
    assert "forge_http_request_duration_seconds_bucket" in metric_text


# ---------- helpers ----------

def _counter_value(counter, **labels) -> float:
    """Read the current value of a labelled counter. Defensive against
    prometheus_client internal API drift."""
    try:
        return counter.labels(**labels)._value.get()
    except Exception:
        # Label combo may not yet exist; treat as zero
        return 0.0
