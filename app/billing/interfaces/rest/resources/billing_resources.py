from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.billing.domain.model.aggregates.billing_cycle import CycleStatus
from app.billing.domain.model.aggregates.payment import PaymentKind


class PaymentTargetResource(BaseModel):
    """Set only the id the kind pays: cycle_id for CYCLE_STATEMENT, installment_id for
    INSTALLMENT and INSTALLMENT_ADVANCE, purchase_id for SINGLE_DATE_EARLY and FULL_PREPAYMENT.
    """

    kind: PaymentKind = Field(examples=["INSTALLMENT"])
    cycle_id: int | None = None
    installment_id: int | None = Field(None, examples=[12])
    purchase_id: int | None = None


class RegisterPaymentResource(PaymentTargetResource):
    # The exact amount due, as the quote returned it: there are no partial payments.
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2, examples=["109.68"])


class PaymentQuoteResource(BaseModel):
    """What paying today takes. interest_days are the days early payments charge interest for."""

    kind: PaymentKind
    customer_id: int
    paid_on: date
    cycle_id: int | None
    installment_id: int | None
    purchase_id: int | None
    late_interest: Decimal
    ordinary_interest: Decimal
    principal: Decimal
    total: Decimal
    savings: Decimal
    days_late: int
    interest_days: int | None


class PaymentResource(BaseModel):
    """customer_id is the account (store_customers.id), as in /customers/{id}."""

    id: int
    customer_id: int
    kind: PaymentKind
    paid_on: date
    cycle_id: int | None
    installment_id: int | None
    purchase_id: int | None
    late_interest: Decimal
    ordinary_interest: Decimal
    principal: Decimal
    total: Decimal
    savings: Decimal
    created_at: datetime


class CycleResource(BaseModel):
    """Totals are null while the cycle is open; once closed they are the issued statement."""

    id: int
    customer_id: int
    year: int
    month: int
    cutoff_date: date
    payment_date: date
    status: CycleStatus
    capital: Decimal | None
    ordinary_interest: Decimal | None
    late_interest: Decimal | None
    total: Decimal | None


class StatementPurchaseResource(BaseModel):
    purchase_id: int
    purchased_at: datetime
    mode: str
    amount: Decimal
    ordinary_interest: Decimal
    status: str


class StatementResource(BaseModel):
    """The statement today. Only single date purchases add to it; weekly purchases are listed
    but are paid installment by installment. An overdue cycle includes late interest to today.
    """

    cycle_id: int
    customer_id: int
    year: int
    month: int
    cutoff_date: date
    payment_date: date
    status: CycleStatus
    capital: Decimal
    ordinary_interest: Decimal
    late_interest: Decimal
    total: Decimal
    purchases: list[StatementPurchaseResource]
