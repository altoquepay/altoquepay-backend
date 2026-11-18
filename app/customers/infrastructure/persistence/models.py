from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base


class CustomerModel(Base):
    __tablename__ = "customers"
    __table_args__ = (CheckConstraint("dni ~ '^[0-9]{8}$'", name="dni_eight_digits"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str] = mapped_column(String(8), unique=True)
    # One user per person, shared by all the stores where they buy.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)


class StoreCustomerModel(Base):
    __tablename__ = "store_customers"
    __table_args__ = (
        UniqueConstraint("store_id", "customer_id", name="uq_store_customers_store_customer"),
        CheckConstraint("currency = 'PEN'", name="currency_pen"),
        CheckConstraint("credit_limit >= 0", name="credit_limit_not_negative"),
        CheckConstraint("tea >= 0", name="tea_not_negative"),
        CheckConstraint("late_tea >= 0", name="late_tea_not_negative"),
        CheckConstraint("cutoff_day BETWEEN 1 AND 25", name="cutoff_day_range"),
        CheckConstraint("payment_day BETWEEN 1 AND 28", name="payment_day_range"),
        CheckConstraint("payment_day > cutoff_day", name="payment_day_after_cutoff"),
        CheckConstraint("max_weeks BETWEEN 1 AND 99", name="max_weeks_range"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status_known"),
        CheckConstraint(
            "(access_code_hash IS NULL) = (access_code_expires_at IS NULL)",
            name="access_code_with_expiry",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    # How this store knows the person; other stores keep their own.
    first_names: Mapped[str] = mapped_column(String(100))
    last_names: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3), server_default="PEN")
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Percentages, as shown to users: 40% is stored as 40.0000000.
    tea: Mapped[Decimal] = mapped_column(Numeric(12, 7))
    late_tea: Mapped[Decimal] = mapped_column(Numeric(12, 7))
    cutoff_day: Mapped[int]
    payment_day: Mapped[int]
    max_weeks: Mapped[int]
    status: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set when the customer redeems the access code of this store; empty hides it from the portal.
    portal_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set once the customer links it; then only a trusted store may restore their access.
    portal_trusted: Mapped[bool] = mapped_column(server_default="false")
    # SHA-256 of the access code in hexadecimal; the code itself is only shown to the store once.
    access_code_hash: Mapped[str | None] = mapped_column(String(64))
    access_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
