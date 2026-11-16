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
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_customer_id: Mapped[int] = mapped_column(ForeignKey("store_customers.id"))
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
