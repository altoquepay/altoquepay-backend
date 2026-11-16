from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base


class BillingCycleModel(Base):
    __tablename__ = "billing_cycles"
    __table_args__ = (
        UniqueConstraint(
            "store_customer_id", "year", "month", name="uq_billing_cycles_account_period"
        ),
        CheckConstraint("month BETWEEN 1 AND 12", name="month_range"),
        CheckConstraint("payment_date > cutoff_date", name="payment_date_after_cutoff"),
        CheckConstraint("status IN ('OPEN', 'CLOSED', 'PAID', 'OVERDUE')", name="status_known"),
        # The daily job looks for cycles that reached their payment date unpaid.
        Index("ix_billing_cycles_payment_date_status", "payment_date", "status"),
        Index("ix_billing_cycles_store_id_year_month", "store_id", "year", "month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_customer_id: Mapped[int] = mapped_column(ForeignKey("store_customers.id"))
    # Copied from the account, so the store's cycles are listed without reading customers.
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    year: Mapped[int]
    month: Mapped[int]
    cutoff_date: Mapped[date]
    payment_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(10))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Fixed when the cycle closes; an open cycle calculates them when queried.
    capital: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ordinary_interest: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    late_interest: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))


class PaymentModel(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('CYCLE_STATEMENT', 'INSTALLMENT', 'INSTALLMENT_ADVANCE',"
            " 'SINGLE_DATE_EARLY', 'FULL_PREPAYMENT')",
            name="kind_known",
        ),
        # Each kind pays exactly one target: a cycle, an installment or a purchase.
        CheckConstraint(
            "(kind = 'CYCLE_STATEMENT') = (billing_cycle_id IS NOT NULL)"
            " AND (kind IN ('INSTALLMENT', 'INSTALLMENT_ADVANCE')) = (installment_id IS NOT NULL)"
            " AND (kind IN ('SINGLE_DATE_EARLY', 'FULL_PREPAYMENT')) = (purchase_id IS NOT NULL)",
            name="target_matches_kind",
        ),
        CheckConstraint(
            "late_interest >= 0 AND ordinary_interest >= 0 AND principal >= 0"
            " AND savings >= 0 AND total = late_interest + ordinary_interest + principal",
            name="amounts_consistent",
        ),
        Index("ix_payments_store_id_paid_on", "store_id", "paid_on"),
        Index("ix_payments_store_customer_id_paid_on", "store_customer_id", "paid_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    store_customer_id: Mapped[int] = mapped_column(ForeignKey("store_customers.id"))
    kind: Mapped[str] = mapped_column(String(19))
    paid_on: Mapped[date]
    late_interest: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    ordinary_interest: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    principal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    savings: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    billing_cycle_id: Mapped[int | None] = mapped_column(ForeignKey("billing_cycles.id"))
    installment_id: Mapped[int | None] = mapped_column(ForeignKey("installments.id"))
    purchase_id: Mapped[int | None] = mapped_column(ForeignKey("purchases.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
