"""add sign in attempts

Revision ID: 3c8dcad76508
Revises: 7cdbcc056b7c
Create Date: 2026-11-17 19:36:19.874777

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c8dcad76508"
down_revision: str | Sequence[str] | None = "7cdbcc056b7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sign_in_attempts",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_sign_in_attempts")),
    )
    op.create_index(
        op.f("ix_sign_in_attempts_window_started_at"),
        "sign_in_attempts",
        ["window_started_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_sign_in_attempts_window_started_at"), table_name="sign_in_attempts")
    op.drop_table("sign_in_attempts")
