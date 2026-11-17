"""add portal access to store_customers

Revision ID: b7e41c9a52d0
Revises: a3f9c2d71e40
Create Date: 2026-11-17 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e41c9a52d0"
down_revision: str | Sequence[str] | None = "a3f9c2d71e40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing accounts stay unlinked: each store links its own with the code it hands over.
    op.add_column(
        "store_customers",
        sa.Column("portal_linked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "store_customers", sa.Column("access_code_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "store_customers",
        sa.Column("access_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_store_customers_access_code_with_expiry"),
        "store_customers",
        "(access_code_hash IS NULL) = (access_code_expires_at IS NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("ck_store_customers_access_code_with_expiry"), "store_customers", type_="check"
    )
    op.drop_column("store_customers", "access_code_expires_at")
    op.drop_column("store_customers", "access_code_hash")
    op.drop_column("store_customers", "portal_linked_at")
