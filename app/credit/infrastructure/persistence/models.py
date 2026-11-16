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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.database import Base


class PurchaseModel(Base):
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint("mode IN ('SINGLE_DATE', 'WEEKLY')", name="mode_known"),
        CheckConstraint("status IN ('ACTIVE', 'PAID', 'PREPAID')", name="status_known"),
        CheckConstraint(
            "(mode = 'SINGLE_DATE' AND term_days IS NOT NULL AND installments_count IS NULL)"
            " OR (mode = 'WEEKLY' AND grace_days IS NOT NULL AND installments_count >= 1"
            " AND capitalized_amount IS NOT NULL AND weekly_rate IS NOT NULL"
            " AND installment_amount IS NOT NULL)",
            name="mode_fields",
        ),
        CheckConstraint("amount >= 0 AND ordinary_interest >= 0", name="amounts_not_negative"),
        CheckConstraint("term_days >= 0 AND grace_days >= 0", name="days_not_negative"),
        Index("ix_purchases_store_customer_id_purchased_at", "store_customer_id", "purchased_at"),
        Index("ix_purchases_store_id_purchased_at", "store_id", "purchased_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    store_customer_id: Mapped[int] = mapped_column(ForeignKey("store_customers.id"))
    billing_cycle_id: Mapped[int] = mapped_column(ForeignKey("billing_cycles.id"))
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(11))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tea: Mapped[Decimal] = mapped_column(Numeric(12, 7))
    late_tea: Mapped[Decimal] = mapped_column(Numeric(12, 7))
    term_days: Mapped[int | None]
    grace_days: Mapped[int | None]
    capitalized_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    weekly_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 7))
    installments_count: Mapped[int | None]
    installment_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ordinary_interest: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(7))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # shortcut: no foreign key until billing creates the payments table; add it then.
    payment_id: Mapped[int | None]

    items: Mapped[list["PurchaseItemModel"]] = relationship(
        lazy="selectin", order_by="PurchaseItemModel.id"
    )
    installments: Mapped[list["InstallmentModel"]] = relationship(
        lazy="selectin", order_by="InstallmentModel.number"
    )


class PurchaseItemModel(Base):
    __tablename__ = "purchase_items"
    __table_args__ = (
        UniqueConstraint("purchase_id", "product_id", name="uq_purchase_items_purchase_product"),
        CheckConstraint("quantity >= 1", name="quantity_positive"),
        CheckConstraint("unit_list_price >= 0", name="unit_list_price_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    unit_list_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class InstallmentModel(Base):
    __tablename__ = "installments"
    __table_args__ = (
        UniqueConstraint("purchase_id", "number", name="uq_installments_purchase_number"),
        # OVERDUE is never stored: it is a pending installment past its due date.
        CheckConstraint("status IN ('PENDING', 'PAID', 'CANCELLED')", name="status_known"),
        CheckConstraint("number >= 1", name="number_positive"),
        Index("ix_installments_due_date_status", "due_date", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    number: Mapped[int]
    due_date: Mapped[date]
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    interest: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amortization: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(9))
    # shortcut: no foreign key until billing creates the payments table; add it then.
    payment_id: Mapped[int | None]
