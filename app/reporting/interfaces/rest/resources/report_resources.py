from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class CustomerStoreResource(BaseModel):
    store_id: int
    business_name: str
    store_status: str
    account_status: str


class InstallmentResource(BaseModel):
    """status is PENDING, or OVERDUE once past its due date."""

    installment_id: int
    purchase_id: int
    number: int
    due_date: date
    amount: Decimal
    status: str


class AccountOverviewResource(BaseModel):
    """installments are every pending and overdue one, by due date."""

    store_id: int
    business_name: str
    account_status: str
    credit_limit: Decimal
    outstanding_principal: Decimal
    available_credit: Decimal
    tea: Decimal
    late_tea: Decimal
    cutoff_day: int
    payment_day: int
    max_weeks: int
    installments: list[InstallmentResource]


class CycleStatementResource(BaseModel):
    cycle_id: int
    year: int
    month: int
    cutoff_date: date
    payment_date: date
    status: str
    capital: Decimal
    ordinary_interest: Decimal
    late_interest: Decimal
    total: Decimal


class PurchaseResource(BaseModel):
    purchase_id: int
    purchased_at: datetime
    mode: str
    amount: Decimal
    tea: Decimal
    term_days: int | None
    installments_count: int | None
    installment_amount: Decimal | None
    ordinary_interest: Decimal
    status: str


class PurchaseScheduleResource(BaseModel):
    """installments are the ones still to pay, by number."""

    purchase: PurchaseResource
    installments: list[InstallmentResource]


class PurchaseTotalsResource(BaseModel):
    count: int
    amount: Decimal
    ordinary_interest: Decimal
    single_date_count: int
    weekly_count: int


class PaymentTotalsResource(BaseModel):
    count: int
    total: Decimal
    principal: Decimal
    ordinary_interest: Decimal
    late_interest: Decimal
    savings: Decimal


class BcrpCapResource(BaseModel):
    max_tea: Decimal
    max_late_tea: Decimal
    valid_from: date
    valid_to: date


class UpcomingDueResource(BaseModel):
    """type is INSTALLMENT for a weekly installment or CYCLE for a cycle statement."""

    type: str
    account_id: int
    customer_name: str
    due_date: date
    amount: Decimal


class DashboardResource(BaseModel):
    """bcrp_cap is null when no cap is in force today: a system admin must register it.

    upcoming lists what falls due in the next 7 days, today included, by due date. next_cutoff
    is the earliest cutoff among the cycles with purchases still open, or null if none is.
    """

    active_customers: int
    outstanding_principal: Decimal
    overdue_installments: int
    overdue_amount: Decimal
    purchases_this_month: PurchaseTotalsResource
    payments_this_month: PaymentTotalsResource
    bcrp_cap: BcrpCapResource | None
    upcoming: list[UpcomingDueResource]
    next_cutoff: date | None


class PeriodReportResource(BaseModel):
    from_date: date
    to_date: date
    purchases: PurchaseTotalsResource
    payments: PaymentTotalsResource
