import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def test_all_tables_exist_with_correct_columns(db_engine):
    inspector = inspect(db_engine)
    table_names = inspector.get_table_names()

    assert "warehouses" in table_names
    assert "products" in table_names
    assert "stock_levels" in table_names

    wh_cols = {c["name"] for c in inspector.get_columns("warehouses")}
    assert {"id", "name", "city"}.issubset(wh_cols)

    prod_cols = {c["name"] for c in inspector.get_columns("products")}
    assert {"id", "sku", "name", "unit", "unit_price", "created_at"}.issubset(prod_cols)

    sl_cols = {c["name"] for c in inspector.get_columns("stock_levels")}
    assert {
        "id", "product_id", "warehouse_id",
        "physical_qty", "reserved_qty", "min_alarm_qty", "updated_at",
    }.issubset(sl_cols)

    fks = inspector.get_foreign_keys("stock_levels")
    referred_tables = {fk["referred_table"] for fk in fks}
    assert "products" in referred_tables
    assert "warehouses" in referred_tables

    uq_col_sets = [
        frozenset(c["column_names"]) for c in inspector.get_unique_constraints("stock_levels")
    ]
    assert frozenset({"product_id", "warehouse_id"}) in uq_col_sets


def test_reserved_exceeds_physical_raises_integrity_error(db_conn):
    db_conn.execute(text("INSERT INTO warehouses (name, city) VALUES ('W-reserved', 'TestCity')"))
    db_conn.execute(text("INSERT INTO products (sku, name) VALUES ('SKU-reserved', 'Test Product')"))
    wh_id = db_conn.execute(
        text("SELECT id FROM warehouses WHERE name = 'W-reserved'")
    ).scalar_one()
    prod_id = db_conn.execute(
        text("SELECT id FROM products WHERE sku = 'SKU-reserved'")
    ).scalar_one()

    with pytest.raises(IntegrityError):
        with db_conn.begin_nested():
            db_conn.execute(
                text(
                    "INSERT INTO stock_levels (product_id, warehouse_id, physical_qty, reserved_qty)"
                    " VALUES (:p, :w, 10.0, 20.0)"
                ),
                {"p": prod_id, "w": wh_id},
            )


def test_negative_physical_qty_raises_integrity_error(db_conn):
    db_conn.execute(text("INSERT INTO warehouses (name, city) VALUES ('W-negative', 'TestCity')"))
    db_conn.execute(text("INSERT INTO products (sku, name) VALUES ('SKU-negative', 'Test Product')"))
    wh_id = db_conn.execute(
        text("SELECT id FROM warehouses WHERE name = 'W-negative'")
    ).scalar_one()
    prod_id = db_conn.execute(
        text("SELECT id FROM products WHERE sku = 'SKU-negative'")
    ).scalar_one()

    with pytest.raises(IntegrityError):
        with db_conn.begin_nested():
            db_conn.execute(
                text(
                    "INSERT INTO stock_levels (product_id, warehouse_id, physical_qty, reserved_qty)"
                    " VALUES (:p, :w, -1.0, 0.0)"
                ),
                {"p": prod_id, "w": wh_id},
            )


def test_duplicate_product_warehouse_raises_unique_violation(db_conn):
    db_conn.execute(text("INSERT INTO warehouses (name, city) VALUES ('W-dup', 'TestCity')"))
    db_conn.execute(text("INSERT INTO products (sku, name) VALUES ('SKU-dup', 'Test Product')"))
    wh_id = db_conn.execute(
        text("SELECT id FROM warehouses WHERE name = 'W-dup'")
    ).scalar_one()
    prod_id = db_conn.execute(
        text("SELECT id FROM products WHERE sku = 'SKU-dup'")
    ).scalar_one()

    db_conn.execute(
        text(
            "INSERT INTO stock_levels (product_id, warehouse_id, physical_qty, reserved_qty)"
            " VALUES (:p, :w, 5.0, 2.0)"
        ),
        {"p": prod_id, "w": wh_id},
    )

    with pytest.raises(IntegrityError):
        with db_conn.begin_nested():
            db_conn.execute(
                text(
                    "INSERT INTO stock_levels (product_id, warehouse_id, physical_qty, reserved_qty)"
                    " VALUES (:p, :w, 3.0, 1.0)"
                ),
                {"p": prod_id, "w": wh_id},
            )
