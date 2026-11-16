"""create products

Revision ID: c81cabd93fcf
Revises: 28fd9a4c3fdd
Create Date: 2026-11-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c81cabd93fcf"
down_revision: str | Sequence[str] | None = "28fd9a4c3fdd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("supplier", sa.String(length=100), nullable=True),
        sa.Column("brand", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("cash_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("list_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint("cash_price >= 0", name=op.f("ck_products_cash_price_not_negative")),
        sa.CheckConstraint("list_price >= 0", name=op.f("ck_products_list_price_not_negative")),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name=op.f("fk_products_store_id_stores")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("store_id", "code", name="uq_products_store_code"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("products")
