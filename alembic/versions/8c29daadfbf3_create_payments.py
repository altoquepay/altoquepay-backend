"""create payments and link cycles to their store

Revision ID: 8c29daadfbf3
Revises: 48f5c26b5112
Create Date: 2026-11-16 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c29daadfbf3"
down_revision: str | Sequence[str] | None = "48f5c26b5112"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Cycles keep their account's store, so a store's cycles are listed without customers.
    op.add_column("billing_cycles", sa.Column("store_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE billing_cycles SET store_id = store_customers.store_id"
        " FROM store_customers WHERE store_customers.id = billing_cycles.store_customer_id"
    )
    op.alter_column("billing_cycles", "store_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_billing_cycles_store_id_stores"), "billing_cycles", "stores", ["store_id"], ["id"]
    )
    op.create_index(
        "ix_billing_cycles_store_id_year_month",
        "billing_cycles",
        ["store_id", "year", "month"],
        unique=False,
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("store_customer_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=19), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("late_interest", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("ordinary_interest", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("principal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("savings", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("billing_cycle_id", sa.Integer(), nullable=True),
        sa.Column("installment_id", sa.Integer(), nullable=True),
        sa.Column("purchase_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('CYCLE_STATEMENT', 'INSTALLMENT', 'INSTALLMENT_ADVANCE',"
            " 'SINGLE_DATE_EARLY', 'FULL_PREPAYMENT')",
            name=op.f("ck_payments_kind_known"),
        ),
        sa.CheckConstraint(
            "(kind = 'CYCLE_STATEMENT') = (billing_cycle_id IS NOT NULL)"
            " AND (kind IN ('INSTALLMENT', 'INSTALLMENT_ADVANCE')) = (installment_id IS NOT NULL)"
            " AND (kind IN ('SINGLE_DATE_EARLY', 'FULL_PREPAYMENT')) = (purchase_id IS NOT NULL)",
            name=op.f("ck_payments_target_matches_kind"),
        ),
        sa.CheckConstraint(
            "late_interest >= 0 AND ordinary_interest >= 0 AND principal >= 0"
            " AND savings >= 0 AND total = late_interest + ordinary_interest + principal",
            name=op.f("ck_payments_amounts_consistent"),
        ),
        sa.ForeignKeyConstraint(
            ["billing_cycle_id"],
            ["billing_cycles.id"],
            name=op.f("fk_payments_billing_cycle_id_billing_cycles"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_payments_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["installment_id"],
            ["installments.id"],
            name=op.f("fk_payments_installment_id_installments"),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"], ["purchases.id"], name=op.f("fk_payments_purchase_id_purchases")
        ),
        sa.ForeignKeyConstraint(
            ["store_customer_id"],
            ["store_customers.id"],
            name=op.f("fk_payments_store_customer_id_store_customers"),
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name=op.f("fk_payments_store_id_stores")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
    )
    op.create_index("ix_payments_store_id_paid_on", "payments", ["store_id", "paid_on"])
    op.create_index(
        "ix_payments_store_customer_id_paid_on", "payments", ["store_customer_id", "paid_on"]
    )

    # The payments table exists now, so what credit marks as paid can reference its payment.
    op.create_foreign_key(
        op.f("fk_purchases_payment_id_payments"), "purchases", "payments", ["payment_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_installments_payment_id_payments"),
        "installments",
        "payments",
        ["payment_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("fk_installments_payment_id_payments"), "installments", type_="foreignkey"
    )
    op.drop_constraint(op.f("fk_purchases_payment_id_payments"), "purchases", type_="foreignkey")
    op.drop_index("ix_payments_store_customer_id_paid_on", table_name="payments")
    op.drop_index("ix_payments_store_id_paid_on", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_billing_cycles_store_id_year_month", table_name="billing_cycles")
    op.drop_constraint(
        op.f("fk_billing_cycles_store_id_stores"), "billing_cycles", type_="foreignkey"
    )
    op.drop_column("billing_cycles", "store_id")
