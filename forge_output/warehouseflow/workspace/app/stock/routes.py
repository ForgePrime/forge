import math
from typing import Optional

from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.middleware import get_current_user
from app.auth.models import User, UserRole
from app.database import get_db
from app.stock.service import StockService

router = APIRouter(prefix="/api", tags=["stock"])


class WarehouseStockOut(BaseModel):
    warehouse_id: int
    warehouse_name: str
    physical_qty: Decimal
    reserved_qty: Decimal
    available_qty: Decimal
    is_below_alarm: bool


class StockRowOut(BaseModel):
    product_id: int
    sku: str
    name: str
    unit: Optional[str]
    warehouses: list[WarehouseStockOut]


class ProductListOut(BaseModel):
    items: list[StockRowOut]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/products", response_model=ProductListOut)
def list_products(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    search: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductListOut:
    service = StockService(db)

    if user.role == UserRole.operator:
        result = service.get_stock_for_warehouse(
            user.warehouse_id, page=page, per_page=per_page, search=search
        )
    else:
        result = service.get_stock_all_warehouses(page=page, per_page=per_page, search=search)

    pages = math.ceil(result.total / result.per_page) if result.total > 0 else 0

    return ProductListOut(
        items=[
            StockRowOut(
                product_id=row.product_id,
                sku=row.sku,
                name=row.name,
                unit=row.unit,
                warehouses=[
                    WarehouseStockOut(
                        warehouse_id=wh.warehouse_id,
                        warehouse_name=wh.warehouse_name,
                        physical_qty=wh.physical_qty,
                        reserved_qty=wh.reserved_qty,
                        available_qty=wh.available_qty,
                        is_below_alarm=wh.is_below_alarm,
                    )
                    for wh in row.warehouses
                ],
            )
            for row in result.items
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=pages,
    )
