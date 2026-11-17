"""create product_images

Revision ID: a3f9c2d71e40
Revises: 8c29daadfbf3
Create Date: 2026-11-17 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f9c2d71e40"
down_revision: str | Sequence[str] | None = "8c29daadfbf3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "product_images",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("name", name=op.f("pk_product_images")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("product_images")
