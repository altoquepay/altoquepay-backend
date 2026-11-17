from datetime import date, datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, Field

from app.credit.domain.model.aggregates.purchase import (
    InstallmentStatus,
    PaymentMode,
    PurchaseStatus,
)


class RequestedItemResource(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=10_000, examples=[4])


class RegisterPurchaseResource(BaseModel):
    # The account of the customer in this store (store_customers.id).
    customer_id: int
    purchased_at: AwareDatetime = Field(examples=["2026-10-15T12:00:00-05:00"])
    mode: PaymentMode
    installments_count: int | None = Field(None, examples=[4])
    items: list[RequestedItemResource] = Field(min_length=1, max_length=100)


class PurchaseItemResource(BaseModel):
    product_id: int
    quantity: int
    unit_list_price: Decimal
    subtotal: Decimal


class InstallmentResource(BaseModel):
    id: int | None
    number: int
    due_date: date
    opening_balance: Decimal
    interest: Decimal
    amortization: Decimal
    amount: Decimal
    closing_balance: Decimal
    status: InstallmentStatus


class PurchaseResource(BaseModel):
    """Rates are percentages. id is null in a simulation. voided_at and voided_by, the user who
    voided it, are set only on a VOIDED purchase."""

    id: int | None
    customer_id: int
    cycle_id: int
    purchased_at: datetime
    mode: PaymentMode
    amount: Decimal
    tea: Decimal
    late_tea: Decimal
    term_days: int | None
    grace_days: int | None
    capitalized_amount: Decimal | None
    weekly_rate: Decimal | None
    installments_count: int | None
    installment_amount: Decimal | None
    ordinary_interest: Decimal
    total: Decimal
    status: PurchaseStatus
    voided_at: datetime | None
    voided_by: int | None


class PurchaseDetailResource(PurchaseResource):
    items: list[PurchaseItemResource]
    installments: list[InstallmentResource]


class InstallmentListItemResource(InstallmentResource):
    purchase_id: int
    customer_id: int
