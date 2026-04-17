"""
Load KPI tests — verify KR0: p95 < 3000ms at 30 concurrent users.

Architecture:
  - pytest fixtures seed data + start a real uvicorn process (port 8765)
  - locust runs headless via subprocess; stats written to temp CSV
  - _parse_stats() extracts p95 and fail_ratio from the Aggregated CSV row
"""
import csv
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from jose import jwt
from sqlalchemy import text

from app.config import ACCESS_TOKEN_EXPIRE_HOURS, ALGORITHM, SECRET_KEY
from tests.load.seed_data import seed, teardown

_WORKSPACE = Path(__file__).parent.parent.parent
_LOCUSTFILE = Path(__file__).parent / "locustfile.py"
_SERVER_HOST = "http://127.0.0.1:8765"
_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://forge:forge@localhost:5432/warehouseflow_test"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def load_data(db_engine):
    """Seed 2000 products × 3 warehouses; teardown after module."""
    data = seed(db_engine)
    yield data
    teardown(db_engine)


@pytest.fixture(scope="module")
def load_token(load_data):
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(load_data["user_id"]), "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


@pytest.fixture(scope="module")
def running_server():
    """Start uvicorn pointed at the test DB; wait for readiness; yield; terminate."""
    env = {
        **os.environ,
        "DATABASE_URL": _TEST_DB_URL,
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
            "--log-level",
            "warning",
        ],
        cwd=str(_WORKSPACE),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(30):
        try:
            r = requests.get(f"{_SERVER_HOST}/api/products", timeout=2)
            # 401 means the server is up (auth required but running)
            if r.status_code in (200, 401, 403, 422):
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("uvicorn did not become ready within 30s on port 8765")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_locust(token: str) -> dict:
    """Run locust headless for 60s with 30 users, return Aggregated stats row."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_prefix = os.path.join(tmpdir, "load")
        cmd = [
            sys.executable,
            "-m",
            "locust",
            "-f",
            str(_LOCUSTFILE),
            "--headless",
            "--host",
            _SERVER_HOST,
            "-u",
            "30",
            "-r",
            "5",
            "--run-time",
            "60s",
            "--csv",
            csv_prefix,
        ]
        env = {**os.environ, "LOAD_TEST_JWT_TOKEN": token}

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=150,
            cwd=str(_WORKSPACE),
        )

        stats_file = csv_prefix + "_stats.csv"
        if not os.path.exists(stats_file):
            raise RuntimeError(
                f"Locust CSV not produced.\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )

        with open(stats_file, newline="") as f:
            rows = list(csv.DictReader(f))

    aggregated = next((r for r in rows if r.get("Name") == "Aggregated"), None)
    if aggregated is None:
        raise RuntimeError(
            f"No 'Aggregated' row in {stats_file}. Rows: {rows}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return aggregated


def _parse_p95(stats: dict) -> float:
    raw = stats.get("95%", "0")
    return float(raw) if raw not in ("N/A", "", "None") else 0.0


def _parse_fail_ratio(stats: dict) -> float:
    total = int(stats.get("Request Count", "0") or "0")
    failures = int(stats.get("Failure Count", "0") or "0")
    return failures / total if total > 0 else 1.0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_product_list_p95_under_3000ms(load_data, load_token, running_server):
    """
    AC-0 (positive): 30 users, 60s, GET /api/products — p95 < 3000ms, error rate < 1%.
    Verifies KR0 with idx_stock_warehouse_product in place.
    """
    stats = _run_locust(load_token)
    p95 = _parse_p95(stats)
    fail_ratio = _parse_fail_ratio(stats)

    assert p95 < 3000, (
        f"KR0 FAILED: p95={p95:.0f}ms exceeds 3000ms threshold "
        f"(requests={stats.get('Request Count')}, failures={stats.get('Failure Count')})"
    )
    assert fail_ratio < 0.01, (
        f"KR0 FAILED: fail_ratio={fail_ratio:.4f} exceeds 1% threshold "
        f"(requests={stats.get('Request Count')}, failures={stats.get('Failure Count')})"
    )


def test_product_list_without_index_exceeds_3000ms(load_data, load_token, db_engine, running_server):
    """
    AC-1 (negative): dropping idx_stock_warehouse_product causes p95 > 3000ms.
    Proves the index is load-bearing for KR0; recreates it in finally.
    """
    with db_engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_stock_warehouse_product"))
        # Force planner to use updated statistics without the index.
        conn.execute(text("ANALYZE stock_levels"))
        conn.commit()

    try:
        stats = _run_locust(load_token)
        p95 = _parse_p95(stats)
    finally:
        with db_engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_stock_warehouse_product "
                    "ON stock_levels (warehouse_id, product_id)"
                )
            )
            conn.commit()

    assert p95 > 3000, (
        f"Expected p95 > 3000ms without index, got {p95:.0f}ms — "
        "index may not be critical at current data volume, or query planner chose a different path"
    )
