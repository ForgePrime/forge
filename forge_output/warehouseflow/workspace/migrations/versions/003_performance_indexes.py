"""performance indexes: stock_levels compound, products sku, products name trgm

Revision ID: 003
Revises: 002
Create Date: 2026-04-17

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "idx_stock_warehouse_product",
        "stock_levels",
        ["warehouse_id", "product_id"],
    )
    op.create_index("idx_products_sku", "products", ["sku"])
    op.execute(
        "CREATE INDEX idx_products_name_trgm ON products USING gin(name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_products_name_trgm")
    op.drop_index("idx_products_sku", table_name="products")
    op.drop_index("idx_stock_warehouse_product", table_name="stock_levels")
