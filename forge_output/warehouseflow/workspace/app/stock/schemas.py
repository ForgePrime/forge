from dataclasses import dataclass, field
from decimal import Decimal
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class WarehouseStock:
    warehouse_id: int
    warehouse_name: str
    physical_qty: Decimal
    reserved_qty: Decimal
    available_qty: Decimal
    is_below_alarm: bool


@dataclass
class StockRow:
    product_id: int
    sku: str
    name: str
    unit: Optional[str]
    warehouses: List[WarehouseStock] = field(default_factory=list)


@dataclass
class Page(Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
