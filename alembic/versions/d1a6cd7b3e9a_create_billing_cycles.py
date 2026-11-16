"""create billing_cycles

Revision ID: d1a6cd7b3e9a
Revises: c81cabd93fcf
Create Date: 2026-11-16 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1a6cd7b3e9a"
down_revision: str | Sequence[str] | None = "c81cabd93fcf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "billing_cycles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_customer_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("cutoff_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capital", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("ordinary_interest", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("late_interest", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.CheckConstraint("month BETWEEN 1 AND 12", name=op.f("ck_billing_cycles_month_range")),
        sa.CheckConstraint(
            "payment_date > cutoff_date", name=op.f("ck_billing_cycles_payment_date_after_cutoff")
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'CLOSED', 'PAID', 'OVERDUE')",
            name=op.f("ck_billing_cycles_status_known"),
        ),
        sa.ForeignKeyConstraint(
            ["store_customer_id"],
            ["store_customers.id"],
            name=op.f("fk_billing_cycles_store_customer_id_store_customers"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_cycles")),
        sa.UniqueConstraint(
            "store_customer_id", "year", "month", name="uq_billing_cycles_account_period"
        ),
    )
    op.create_index(
        "ix_billing_cycles_payment_date_status",
        "billing_cycles",
        ["payment_date", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_billing_cycles_payment_date_status", table_name="billing_cycles")
    op.drop_table("billing_cycles")
