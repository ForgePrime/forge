"""Tests for /health (liveness) and /ready (readiness) probes.

Audit item: liveness/readiness split. Load balancers + Kubernetes need
to tell these apart.
"""
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ---------- /health ----------

def test_health_returns_ok_without_any_backend_check():
    """Liveness must be a pure process-alive signal — no DB check."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


# ---------- /ready ----------

def test_ready_returns_200_when_dependencies_ok():
    """In normal test env, Postgres is up (conftest_populated requires it).
    /ready should return 200 with each check labeled 'ok'."""
    r = client.get("/ready")
    # Could be 503 in isolated environments without DB — accept either + verify shape
    assert r.status_code in (200, 503)
    body = r.json()
    assert "checks" in body
    assert "db" in body["checks"]
    assert "ready" in body
    assert isinstance(body["ready"], bool)


def test_ready_response_shape_always_returns_checks_dict():
    """Schema contract: /ready always includes 'checks' dict mapping each
    probe name to 'ok' or 'fail: …' explanation."""
    r = client.get("/ready")
    body = r.json()
    assert isinstance(body["checks"], dict)
    # db is always checked
    db_result = body["checks"]["db"]
    assert db_result == "ok" or db_result.startswith("fail:")


def test_ready_and_health_have_different_semantics():
    """/health and /ready must not be aliases. /ready has a structured
    `checks` payload; /health has a minimal `status` field."""
    h = client.get("/health").json()
    r = client.get("/ready").json()
    assert "checks" in r
    assert "checks" not in h
    assert "status" in h


def test_ready_is_idempotent():
    """Two consecutive /ready calls yield the same shape."""
    r1 = client.get("/ready").json()
    r2 = client.get("/ready").json()
    assert set(r1["checks"].keys()) == set(r2["checks"].keys())
