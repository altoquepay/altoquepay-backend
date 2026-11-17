"""add portal_trusted to store_customers

Revision ID: e5b19d4c7a32
Revises: c2d85f3a9b17
Create Date: 2026-11-17 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b19d4c7a32"
down_revision: str | Sequence[str] | None = "c2d85f3a9b17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "store_customers",
        sa.Column("portal_trusted", sa.Boolean(), server_default="false", nullable=False),
    )
    # Every account the customer linked so far was linked by them, so it is trusted.
    op.execute("UPDATE store_customers SET portal_trusted = portal_linked_at IS NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("store_customers", "portal_trusted")
