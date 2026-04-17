from decimal import Decimal

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from .schemas import Page, StockRow, WarehouseStock


class StockService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_stock_for_warehouse(
        self, warehouse_id: int, page: int, per_page: int, search: str | None = None
    ) -> "Page[StockRow]":
        offset = (page - 1) * per_page
        search_pattern = f"%{search}%" if search is not None else None

        total: int = self._session.execute(
            text(
                "SELECT COUNT(*) FROM products"
                " WHERE (:search IS NULL OR sku ILIKE :search OR name ILIKE :search)"
            ),
            {"search": search_pattern},
        ).scalar_one()

        sql = text("""
            SELECT
                p.id                                                        AS product_id,
                p.sku,
                p.name,
                p.unit,
                w.id                                                        AS warehouse_id,
                w.name                                                      AS warehouse_name,
                COALESCE(sl.physical_qty, 0)                                AS physical_qty,
                COALESCE(sl.reserved_qty, 0)                                AS reserved_qty,
                COALESCE(sl.physical_qty, 0) - COALESCE(sl.reserved_qty, 0) AS available_qty,
                (COALESCE(sl.physical_qty, 0) - COALESCE(sl.reserved_qty, 0))
                    < COALESCE(sl.min_alarm_qty, 0)                         AS is_below_alarm
            FROM products p
            CROSS JOIN (SELECT id, name FROM warehouses WHERE id = :warehouse_id) w
            LEFT JOIN stock_levels sl
                   ON sl.product_id = p.id AND sl.warehouse_id = w.id
            WHERE (:search IS NULL OR p.sku ILIKE :search OR p.name ILIKE :search)
            ORDER BY p.id
            LIMIT :per_page OFFSET :offset
        """)

        rows = self._session.execute(
            sql,
            {"warehouse_id": warehouse_id, "per_page": per_page, "offset": offset, "search": search_pattern},
        ).mappings().all()

        items = [
            StockRow(
                product_id=row["product_id"],
                sku=row["sku"],
                name=row["name"],
                unit=row["unit"],
                warehouses=[
                    WarehouseStock(
                        warehouse_id=row["warehouse_id"],
                        warehouse_name=row["warehouse_name"],
                        physical_qty=Decimal(str(row["physical_qty"])),
                        reserved_qty=Decimal(str(row["reserved_qty"])),
                        available_qty=Decimal(str(row["available_qty"])),
                        is_below_alarm=bool(row["is_below_alarm"]),
                    )
                ],
            )
            for row in rows
        ]

        return Page(items=items, total=total, page=page, per_page=per_page)

    def get_stock_all_warehouses(
        self, page: int, per_page: int, search: str | None = None
    ) -> "Page[StockRow]":
        offset = (page - 1) * per_page
        search_pattern = f"%{search}%" if search is not None else None

        total: int = self._session.execute(
            text(
                "SELECT COUNT(*) FROM products"
                " WHERE (:search IS NULL OR sku ILIKE :search OR name ILIKE :search)"
            ),
            {"search": search_pattern},
        ).scalar_one()

        product_ids: list[int] = [
            row[0]
            for row in self._session.execute(
                text(
                    "SELECT id FROM products"
                    " WHERE (:search IS NULL OR sku ILIKE :search OR name ILIKE :search)"
                    " ORDER BY id LIMIT :lim OFFSET :off"
                ),
                {"lim": per_page, "off": offset, "search": search_pattern},
            ).all()
        ]

        if not product_ids:
            return Page(items=[], total=total, page=page, per_page=per_page)

        sql = text("""
            SELECT
                p.id                                                        AS product_id,
                p.sku,
                p.name,
                p.unit,
                w.id                                                        AS warehouse_id,
                w.name                                                      AS warehouse_name,
                COALESCE(sl.physical_qty, 0)                                AS physical_qty,
                COALESCE(sl.reserved_qty, 0)                                AS reserved_qty,
                COALESCE(sl.physical_qty, 0) - COALESCE(sl.reserved_qty, 0) AS available_qty,
                (COALESCE(sl.physical_qty, 0) - COALESCE(sl.reserved_qty, 0))
                    < COALESCE(sl.min_alarm_qty, 0)                         AS is_below_alarm
            FROM products p
            CROSS JOIN warehouses w
            LEFT JOIN stock_levels sl
                   ON sl.product_id = p.id AND sl.warehouse_id = w.id
            WHERE p.id IN :product_ids
            ORDER BY p.id, w.id
        """).bindparams(bindparam("product_ids", expanding=True))

        rows = self._session.execute(
            sql, {"product_ids": product_ids}
        ).mappings().all()

        products_map: dict[int, StockRow] = {}
        for row in rows:
            pid = row["product_id"]
            if pid not in products_map:
                products_map[pid] = StockRow(
                    product_id=pid,
                    sku=row["sku"],
                    name=row["name"],
                    unit=row["unit"],
                )
            products_map[pid].warehouses.append(
                WarehouseStock(
                    warehouse_id=row["warehouse_id"],
                    warehouse_name=row["warehouse_name"],
                    physical_qty=Decimal(str(row["physical_qty"])),
                    reserved_qty=Decimal(str(row["reserved_qty"])),
                    available_qty=Decimal(str(row["available_qty"])),
                    is_below_alarm=bool(row["is_below_alarm"]),
                )
            )

        items = [products_map[pid] for pid in product_ids if pid in products_map]
        return Page(items=items, total=total, page=page, per_page=per_page)
