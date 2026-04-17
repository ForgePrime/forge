"""
Standalone seeder for load tests.
Can be imported by pytest fixtures (pass engine) or run directly (uses DATABASE_URL env).
"""
import os

import bcrypt as _bcrypt
from sqlalchemy import create_engine, text

_LOAD_DIR_EMAIL = "load_director@test.example"
_LOAD_WH_LIKE = "LoadWH%"
_LOAD_SKU_LIKE = "LOAD-%"


def seed(engine=None):
    """Insert 2000 products × 3 warehouses (6000 stock_levels) + director user.

    Returns dict: {user_id, warehouse_ids}.
    Pre-cleans leftovers from any aborted previous run before inserting.
    """
    if engine is None:
        url = os.environ.get(
            "DATABASE_URL", "postgresql://forge:forge@localhost:5432/warehouseflow_test"
        )
        engine = create_engine(url)

    with engine.connect() as conn:
        conn.execute(
            text(
                "DELETE FROM stock_levels "
                "WHERE warehouse_id IN (SELECT id FROM warehouses WHERE name LIKE 'LoadWH%')"
            )
        )
        conn.execute(text("DELETE FROM products WHERE sku LIKE 'LOAD-%'"))
        conn.execute(text("DELETE FROM warehouses WHERE name LIKE 'LoadWH%'"))
        conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": _LOAD_DIR_EMAIL})
        conn.commit()

    with engine.connect() as conn:
        wh_rows = conn.execute(
            text("""
                INSERT INTO warehouses (name, city)
                VALUES ('LoadWH1', 'CityA'), ('LoadWH2', 'CityB'), ('LoadWH3', 'CityC')
                RETURNING id
            """)
        )
        warehouse_ids = [row[0] for row in wh_rows]

        conn.execute(
            text("""
                INSERT INTO products (sku, name, unit)
                SELECT
                    'LOAD-' || LPAD(i::text, 4, '0'),
                    'Load Test Product ' || LPAD(i::text, 4, '0'),
                    'szt'
                FROM generate_series(1, 2000) AS s(i)
            """)
        )

        conn.execute(
            text("""
                INSERT INTO stock_levels (product_id, warehouse_id, physical_qty, reserved_qty, min_alarm_qty)
                SELECT p.id, w.id, 100, 10, 5
                FROM products p
                CROSS JOIN warehouses w
                WHERE p.sku LIKE 'LOAD-%' AND w.name LIKE 'LoadWH%'
            """)
        )

        pwd_hash = _bcrypt.hashpw(b"loadpass", _bcrypt.gensalt()).decode()
        user_row = conn.execute(
            text("""
                INSERT INTO users (email, password_hash, role)
                VALUES (:email, :hash, 'director')
                RETURNING id
            """),
            {"email": _LOAD_DIR_EMAIL, "hash": pwd_hash},
        )
        user_id = user_row.scalar_one()
        conn.commit()

    return {"user_id": user_id, "warehouse_ids": warehouse_ids}


def teardown(engine=None):
    """Remove seeded load test data in FK-safe order."""
    if engine is None:
        url = os.environ.get(
            "DATABASE_URL", "postgresql://forge:forge@localhost:5432/warehouseflow_test"
        )
        engine = create_engine(url)

    with engine.connect() as conn:
        conn.execute(
            text(
                "DELETE FROM stock_levels "
                "WHERE warehouse_id IN (SELECT id FROM warehouses WHERE name LIKE 'LoadWH%')"
            )
        )
        conn.execute(text("DELETE FROM products WHERE sku LIKE 'LOAD-%'"))
        conn.execute(text("DELETE FROM warehouses WHERE name LIKE 'LoadWH%'"))
        conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": _LOAD_DIR_EMAIL})
        conn.commit()
