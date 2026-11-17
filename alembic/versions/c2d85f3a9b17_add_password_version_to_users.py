"""add password_version to users

Revision ID: c2d85f3a9b17
Revises: b7e41c9a52d0
Create Date: 2026-11-17 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d85f3a9b17"
down_revision: str | Sequence[str] | None = "b7e41c9a52d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("password_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "password_version")
