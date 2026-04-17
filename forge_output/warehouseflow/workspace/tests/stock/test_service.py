from decimal import Decimal

import pytest
from sqlalchemy import text

from app.stock.service import StockService


@pytest.fixture
def warehouse(db_session):
    row = db_session.execute(
        text(
            "INSERT INTO warehouses (name, city) VALUES (:name, :city)"
            " RETURNING id, name"
        ),
        {"name": "Magazyn A", "city": "Warszawa"},
    ).mappings().one()
    return {"id": row["id"], "name": row["name"]}


@pytest.fixture
def product(db_session):
    product_id = db_session.execute(
        text(
            "INSERT INTO products (sku, name, unit)"
            " VALUES (:sku, :name, CAST(:unit AS unit_type)) RETURNING id"
        ),
        {"sku": "SKU-001", "name": "Produkt Testowy", "unit": "szt"},
    ).scalar_one()
    return {"id": product_id}


def test_available_qty_equals_physical_minus_reserved(db_session, warehouse, product):
    """AC-0: 50 physical - 20 reserved = 30 available, computed in SQL."""
    db_session.execute(
        text(
            "INSERT INTO stock_levels"
            " (product_id, warehouse_id, physical_qty, reserved_qty, min_alarm_qty)"
            " VALUES (:pid, :wid, 50, 20, 5)"
        ),
        {"pid": product["id"], "wid": warehouse["id"]},
    )

    service = StockService(db_session)
    page = service.get_stock_for_warehouse(warehouse["id"], page=1, per_page=10)

    assert len(page.items) == 1
    ws = page.items[0].warehouses[0]
    assert ws.physical_qty == Decimal("50")
    assert ws.reserved_qty == Decimal("20")
    assert ws.available_qty == Decimal("30")


def test_alarm_flag_at_exact_boundary_values(db_session, warehouse, product):
    """AC-1: is_below_alarm False when available==min_alarm, True when available==min_alarm-0.001."""
    db_session.execute(
        text(
            "INSERT INTO stock_levels"
            " (product_id, warehouse_id, physical_qty, reserved_qty, min_alarm_qty)"
            " VALUES (:pid, :wid, 100, 70, 30)"
        ),
        {"pid": product["id"], "wid": warehouse["id"]},
    )

    service = StockService(db_session)

    page = service.get_stock_for_warehouse(warehouse["id"], page=1, per_page=10)
    ws = page.items[0].warehouses[0]
    assert ws.available_qty == Decimal("30")
    assert ws.is_below_alarm is False, "available==min_alarm should NOT trigger alarm"

    db_session.execute(
        text(
            "UPDATE stock_levels SET reserved_qty = 70.001"
            " WHERE product_id = :pid AND warehouse_id = :wid"
        ),
        {"pid": product["id"], "wid": warehouse["id"]},
    )

    page2 = service.get_stock_for_warehouse(warehouse["id"], page=1, per_page=10)
    ws2 = page2.items[0].warehouses[0]
    assert ws2.available_qty == Decimal("29.999")
    assert ws2.is_below_alarm is True, "available==min_alarm-0.001 MUST trigger alarm"


def test_missing_stock_level_returns_zeros_not_null(db_session, warehouse, product):
    """AC-2: Product with no stock_level row for warehouse → zeros via LEFT JOIN, not NULL."""
    service = StockService(db_session)
    page = service.get_stock_for_warehouse(warehouse["id"], page=1, per_page=10)

    assert len(page.items) == 1
    ws = page.items[0].warehouses[0]
    assert ws.physical_qty == Decimal("0"), "missing stock_level must yield physical=0"
    assert ws.reserved_qty == Decimal("0"), "missing stock_level must yield reserved=0"
    assert ws.available_qty == Decimal("0"), "missing stock_level must yield available=0"
    assert ws.is_below_alarm is False, "0 available vs 0 min_alarm is not below alarm"
