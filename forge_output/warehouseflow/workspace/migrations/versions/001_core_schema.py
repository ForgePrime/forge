"""core schema: warehouses, products, stock_levels

Revision ID: 001
Revises:
Create Date: 2026-04-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("city", sa.String(50), nullable=True),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.Enum("szt", "kg", "m", name="unit_type"), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
    )

    op.create_table(
        "stock_levels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column(
            "physical_qty",
            sa.Numeric(10, 3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "reserved_qty",
            sa.Numeric(10, 3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "min_alarm_qty",
            sa.Numeric(10, 3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_stock_product",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name="fk_stock_warehouse",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "product_id", "warehouse_id", name="uq_stock_product_warehouse"
        ),
        sa.CheckConstraint("physical_qty >= 0", name="chk_physical_qty_non_negative"),
        sa.CheckConstraint("reserved_qty >= 0", name="chk_reserved_qty_non_negative"),
        sa.CheckConstraint(
            "reserved_qty <= physical_qty", name="chk_reserved_lte_physical"
        ),
    )


def downgrade() -> None:
    op.drop_table("stock_levels")
    op.drop_table("products")
    op.drop_table("warehouses")
    postgresql.ENUM(name="unit_type").drop(op.get_bind(), checkfirst=True)
