"""add voiding to purchases

Revision ID: 7cdbcc056b7c
Revises: 64bc8f7a560c
Create Date: 2026-11-17 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7cdbcc056b7c"
down_revision: str | Sequence[str] | None = "64bc8f7a560c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f("ck_purchases_status_known"), "purchases", type_="check")
    op.create_check_constraint(
        op.f("ck_purchases_status_known"),
        "purchases",
        "status IN ('ACTIVE', 'PAID', 'PREPAID', 'VOIDED')",
    )
    op.add_column("purchases", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchases", sa.Column("voided_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_purchases_voided_by_users"), "purchases", "users", ["voided_by"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # A voided purchase has no status before this revision; refuse instead of deleting it.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM purchases WHERE status = 'VOIDED') THEN
                RAISE EXCEPTION 'There are voided purchases: remove them before downgrading.';
            END IF;
        END $$
        """
    )
    op.drop_constraint(op.f("fk_purchases_voided_by_users"), "purchases", type_="foreignkey")
    op.drop_column("purchases", "voided_by")
    op.drop_column("purchases", "voided_at")
    op.drop_constraint(op.f("ck_purchases_status_known"), "purchases", type_="check")
    op.create_check_constraint(
        op.f("ck_purchases_status_known"), "purchases", "status IN ('ACTIVE', 'PAID', 'PREPAID')"
    )
