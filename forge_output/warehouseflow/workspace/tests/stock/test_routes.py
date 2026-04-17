import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://forge:forge@localhost:5432/warehouseflow_test"
)

import bcrypt
import pytest
from jose import jwt
from sqlalchemy import text

from app.config import ALGORITHM, SECRET_KEY


# ---------------------------------------------------------------------------
# Session-scoped fixtures: insert committed data visible to the app's own DB
# sessions; clean up after the whole test session.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def stock_route_data(db_engine):
    """
    Insert 3 warehouses, 3 products (2 matching 'MP-STL'), 2 users (operator /
    director) and stock_levels for every (product, warehouse) pair.
    Committed so the app's get_db sessions can see the rows.
    """
    with db_engine.connect() as conn:
        w1_id = conn.execute(
            text("INSERT INTO warehouses (name, city) VALUES ('Route-Warsaw', 'Warsaw') RETURNING id")
        ).scalar_one()
        w2_id = conn.execute(
            text("INSERT INTO warehouses (name, city) VALUES ('Route-Gdansk', 'Gdansk') RETURNING id")
        ).scalar_one()
        w3_id = conn.execute(
            text("INSERT INTO warehouses (name, city) VALUES ('Route-Krakow', 'Krakow') RETURNING id")
        ).scalar_one()

        p1_id = conn.execute(
            text(
                "INSERT INTO products (sku, name, unit, unit_price)"
                " VALUES ('MP-STL-001', 'Steel Pipe', 'szt', 10.00) RETURNING id"
            )
        ).scalar_one()
        p2_id = conn.execute(
            text(
                "INSERT INTO products (sku, name, unit, unit_price)"
                " VALUES ('RT-PROD-002', 'Widget', 'kg', 5.00) RETURNING id"
            )
        ).scalar_one()
        p3_id = conn.execute(
            text(
                "INSERT INTO products (sku, name, unit, unit_price)"
                " VALUES ('RT-PROD-003', 'MP-STL Connector', 'szt', 7.00) RETURNING id"
            )
        ).scalar_one()

        op_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
        op_id = conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, warehouse_id)"
                " VALUES ('rt_operator@test.example', :h, 'operator', :wid) RETURNING id"
            ),
            {"h": op_hash, "wid": w1_id},
        ).scalar_one()

        dir_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
        dir_id = conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, warehouse_id)"
                " VALUES ('rt_director@test.example', :h, 'director', NULL) RETURNING id"
            ),
            {"h": dir_hash},
        ).scalar_one()

        for p_id in (p1_id, p2_id, p3_id):
            for w_id in (w1_id, w2_id, w3_id):
                conn.execute(
                    text(
                        "INSERT INTO stock_levels"
                        " (product_id, warehouse_id, physical_qty, reserved_qty, min_alarm_qty)"
                        " VALUES (:pid, :wid, 100, 10, 5)"
                    ),
                    {"pid": p_id, "wid": w_id},
                )

        conn.commit()

    data = {
        "warehouse_ids": [w1_id, w2_id, w3_id],
        "product_ids": [p1_id, p2_id, p3_id],
        "operator_id": op_id,
        "director_id": dir_id,
        "operator_warehouse_id": w1_id,
        "operator_token": jwt.encode({"sub": str(op_id)}, SECRET_KEY, algorithm=ALGORITHM),
        "director_token": jwt.encode({"sub": str(dir_id)}, SECRET_KEY, algorithm=ALGORITHM),
    }

    yield data

    with db_engine.connect() as conn:
        for p_id in (p1_id, p2_id, p3_id):
            conn.execute(text("DELETE FROM stock_levels WHERE product_id = :id"), {"id": p_id})
            conn.execute(text("DELETE FROM products WHERE id = :id"), {"id": p_id})
        for u_id in (op_id, dir_id):
            conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": u_id})
        for w_id in (w1_id, w2_id, w3_id):
            conn.execute(text("DELETE FROM warehouses WHERE id = :id"), {"id": w_id})
        conn.commit()


@pytest.fixture(scope="session")
def stock_client(stock_route_data):
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests (names must match the AC exactly)
# ---------------------------------------------------------------------------

def test_operator_response_has_single_warehouse_per_item(stock_client, stock_route_data):
    token = stock_route_data["operator_token"]
    r = stock_client.get(
        "/api/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    # Only items inserted by this fixture are guaranteed; filter by known product IDs
    known_pids = set(stock_route_data["product_ids"])
    our_items = [i for i in body["items"] if i["product_id"] in known_pids]
    assert len(our_items) == 3, f"Expected 3 products, got {len(our_items)}"
    for item in our_items:
        # Operator (warehouse W1) sees exactly 1 warehouse entry per product
        assert len(item["warehouses"]) == 1, (
            f"Product {item['sku']} has {len(item['warehouses'])} warehouses, expected 1"
        )
        assert item["warehouses"][0]["warehouse_id"] == stock_route_data["operator_warehouse_id"]


def test_director_response_has_all_warehouses_per_item(stock_client, stock_route_data):
    token = stock_route_data["director_token"]
    r = stock_client.get(
        "/api/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    known_pids = set(stock_route_data["product_ids"])
    our_items = [i for i in body["items"] if i["product_id"] in known_pids]
    assert len(our_items) == 3, f"Expected 3 products, got {len(our_items)}"
    n_warehouses = len(stock_route_data["warehouse_ids"])  # 3
    for item in our_items:
        returned_wh_ids = {wh["warehouse_id"] for wh in item["warehouses"]}
        # Director sees ALL warehouses — our 3 must all appear
        for wh_id in stock_route_data["warehouse_ids"]:
            assert wh_id in returned_wh_ids, (
                f"Product {item['sku']} missing warehouse {wh_id}"
            )
        # And the total count equals the number of warehouses we created
        assert len(item["warehouses"]) == n_warehouses, (
            f"Product {item['sku']} has {len(item['warehouses'])} warehouses, expected {n_warehouses}"
        )


def test_unauthenticated_returns_401(stock_client):
    r = stock_client.get("/api/products")
    assert r.status_code == 401


def test_per_page_over_200_returns_422(stock_client, stock_route_data):
    token = stock_route_data["operator_token"]
    r = stock_client.get(
        "/api/products?per_page=201",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_search_filter_returns_matching_products_only(stock_client, stock_route_data):
    token = stock_route_data["operator_token"]
    r = stock_client.get(
        "/api/products?search=MP-STL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    # Filter to items we know about
    known_pids = set(stock_route_data["product_ids"])
    our_items = [i for i in body["items"] if i["product_id"] in known_pids]
    # Only P1 (sku=MP-STL-001) and P3 (name=MP-STL Connector) should match
    skus = {i["sku"] for i in our_items}
    assert "MP-STL-001" in skus, "Expected MP-STL-001 (SKU match) in results"
    assert "RT-PROD-003" in skus, "Expected RT-PROD-003 (name match 'MP-STL Connector') in results"
    assert "RT-PROD-002" not in skus, "Expected RT-PROD-002 (no match) to be excluded"
    # All returned items must match the search term
    for item in our_items:
        matches = "mp-stl" in item["sku"].lower() or "mp-stl" in item["name"].lower()
        assert matches, f"Product {item['sku']} / '{item['name']}' does not match 'MP-STL'"
