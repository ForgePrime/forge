import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://forge:forge@localhost:5432/warehouseflow_test"
)

from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import text

from app.config import ACCESS_TOKEN_EXPIRE_HOURS, ALGORITHM, SECRET_KEY
from app.main import app

_PERF_DIR_EMAIL = "perf_director@test.example"
_PERF_SKU_LIKE = "PERF-%"
_PERF_WH_NAME_LIKE = "PerfWH%"


@pytest.fixture(scope="module")
def perf_setup(db_engine, run_migrations):
    """
    Inserts 2000 products × 3 warehouses (6000 stock_levels) and a director user.
    Pre-cleans any leftovers from aborted previous runs, then re-inserts fresh.
    All data is committed so it's visible to the FastAPI TestClient.
    """
    with db_engine.connect() as conn:
        # Pre-cleanup: guard against leftover data from a previously aborted run.
        conn.execute(text(
            "DELETE FROM stock_levels "
            "WHERE warehouse_id IN (SELECT id FROM warehouses WHERE name LIKE 'PerfWH%')"
        ))
        conn.execute(text("DELETE FROM products WHERE sku LIKE 'PERF-%'"))
        conn.execute(text("DELETE FROM warehouses WHERE name LIKE 'PerfWH%'"))
        conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": _PERF_DIR_EMAIL})
        conn.commit()

    with db_engine.connect() as conn:
        # 3 warehouses
        wh_rows = conn.execute(text("""
            INSERT INTO warehouses (name, city)
            VALUES ('PerfWH1', 'CityA'), ('PerfWH2', 'CityB'), ('PerfWH3', 'CityC')
            RETURNING id
        """))
        warehouse_ids = [row[0] for row in wh_rows]

        # 2000 products via generate_series — single statement, no per-row round-trips.
        conn.execute(text("""
            INSERT INTO products (sku, name, unit)
            SELECT
                'PERF-' || LPAD(i::text, 4, '0'),
                'Performance Product ' || LPAD(i::text, 4, '0'),
                'szt'
            FROM generate_series(1, 2000) AS s(i)
        """))
        product_ids = [
            row[0]
            for row in conn.execute(
                text("SELECT id FROM products WHERE sku LIKE 'PERF-%' ORDER BY id")
            )
        ]

        # 6000 stock_levels via cross join — single statement.
        conn.execute(text("""
            INSERT INTO stock_levels (product_id, warehouse_id, physical_qty, reserved_qty, min_alarm_qty)
            SELECT p.id, w.id, 100, 10, 5
            FROM products p
            CROSS JOIN warehouses w
            WHERE p.sku LIKE 'PERF-%' AND w.name LIKE 'PerfWH%'
        """))

        # Director user — can see all warehouses (required by /api/products all-warehouses path).
        pwd_hash = _bcrypt.hashpw(b"perfpass", _bcrypt.gensalt()).decode()
        user_row = conn.execute(
            text("""
                INSERT INTO users (email, password_hash, role)
                VALUES (:email, :hash, 'director')
                RETURNING id
            """),
            {"email": _PERF_DIR_EMAIL, "hash": pwd_hash},
        )
        user_id = user_row.scalar_one()
        conn.commit()

    yield {
        "warehouse_ids": warehouse_ids,
        "product_ids": product_ids,
        "user_id": user_id,
    }

    # Teardown — delete in FK-safe order.
    with db_engine.connect() as conn:
        conn.execute(text(
            "DELETE FROM stock_levels "
            "WHERE warehouse_id IN (SELECT id FROM warehouses WHERE name LIKE 'PerfWH%')"
        ))
        conn.execute(text("DELETE FROM products WHERE sku LIKE 'PERF-%'"))
        conn.execute(text("DELETE FROM warehouses WHERE name LIKE 'PerfWH%'"))
        conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": _PERF_DIR_EMAIL})
        conn.commit()


@pytest.fixture(scope="module")
def perf_token(perf_setup):
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(perf_setup["user_id"]), "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


@pytest.fixture(scope="module")
def perf_client(perf_setup, perf_token):
    with TestClient(app) as client:
        client.headers.update({"Authorization": f"Bearer {perf_token}"})
        yield client
