"""create customers and store_customers

Revision ID: 28fd9a4c3fdd
Revises: 3604230b4eb3
Create Date: 2026-11-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "28fd9a4c3fdd"
down_revision: str | Sequence[str] | None = "3604230b4eb3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dni", sa.String(length=8), nullable=False),
        sa.Column("first_names", sa.String(length=100), nullable=False),
        sa.Column("last_names", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=200), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("dni ~ '^[0-9]{8}$'", name=op.f("ck_customers_dni_eight_digits")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_customers_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customers")),
        sa.UniqueConstraint("dni", name=op.f("uq_customers_dni")),
        sa.UniqueConstraint("user_id", name=op.f("uq_customers_user_id")),
    )
    op.create_table(
        "store_customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="PEN", nullable=False),
        sa.Column("credit_limit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tea", sa.Numeric(precision=12, scale=7), nullable=False),
        sa.Column("late_tea", sa.Numeric(precision=12, scale=7), nullable=False),
        sa.Column("cutoff_day", sa.Integer(), nullable=False),
        sa.Column("payment_day", sa.Integer(), nullable=False),
        sa.Column("max_weeks", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("currency = 'PEN'", name=op.f("ck_store_customers_currency_pen")),
        sa.CheckConstraint(
            "credit_limit >= 0", name=op.f("ck_store_customers_credit_limit_not_negative")
        ),
        sa.CheckConstraint("tea >= 0", name=op.f("ck_store_customers_tea_not_negative")),
        sa.CheckConstraint("late_tea >= 0", name=op.f("ck_store_customers_late_tea_not_negative")),
        sa.CheckConstraint(
            "cutoff_day BETWEEN 1 AND 25", name=op.f("ck_store_customers_cutoff_day_range")
        ),
        sa.CheckConstraint(
            "payment_day BETWEEN 1 AND 28", name=op.f("ck_store_customers_payment_day_range")
        ),
        sa.CheckConstraint(
            "payment_day > cutoff_day", name=op.f("ck_store_customers_payment_day_after_cutoff")
        ),
        sa.CheckConstraint(
            "max_weeks BETWEEN 1 AND 99", name=op.f("ck_store_customers_max_weeks_range")
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')", name=op.f("ck_store_customers_status_known")
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name=op.f("fk_store_customers_customer_id_customers"),
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name=op.f("fk_store_customers_store_id_stores")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_store_customers")),
        sa.UniqueConstraint("store_id", "customer_id", name="uq_store_customers_store_customer"),
    )
    op.create_index(
        op.f("ix_store_customers_customer_id"), "store_customers", ["customer_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_store_customers_customer_id"), table_name="store_customers")
    op.drop_table("store_customers")
    op.drop_table("customers")
