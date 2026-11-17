"""The store administrator's dashboard and period report."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.regulation.interfaces.acl.regulation_facade import CurrentCap
from app.reporting.application.ports.readers import (
    BillingReader,
    CreditReader,
    CustomerAccounts,
    RateCaps,
)
from app.shared.domain.errors import BusinessError

ZERO = Decimal("0.00")
FIRST_DAY = date(1, 1, 1)
UPCOMING_DAYS = 7
INSTALLMENT = "INSTALLMENT"
CYCLE = "CYCLE"


@dataclass(frozen=True)
class PurchaseTotals:
    count: int
    amount: Decimal
    ordinary_interest: Decimal
    single_date_count: int
    weekly_count: int


@dataclass(frozen=True)
class PaymentTotals:
    count: int
    total: Decimal
    principal: Decimal
    ordinary_interest: Decimal
    late_interest: Decimal
    savings: Decimal


@dataclass(frozen=True)
class UpcomingDue:
    """type is INSTALLMENT for a weekly installment or CYCLE for a cycle statement."""

    type: str
    account_id: int
    customer_name: str
    due_date: date
    amount: Decimal


@dataclass(frozen=True)
class Dashboard:
    active_customers: int
    outstanding_principal: Decimal
    overdue_installments: int
    overdue_statements: int
    overdue_amount: Decimal
    purchases_this_month: PurchaseTotals
    payments_this_month: PaymentTotals
    bcrp_cap: CurrentCap | None
    upcoming: list[UpcomingDue]
    next_cutoff: date | None


@dataclass(frozen=True)
class PeriodReport:
    from_date: date
    to_date: date
    purchases: PurchaseTotals
    payments: PaymentTotals


class StoreReportService:
    """Each figure comes from one store-wide facade call, whatever the number of customers."""

    def __init__(
        self,
        accounts: CustomerAccounts,
        credit: CreditReader,
        billing: BillingReader,
        caps: RateCaps,
    ) -> None:
        self._accounts = accounts
        self._credit = credit
        self._billing = billing
        self._caps = caps

    async def dashboard(self, store_id: int, today: date) -> Dashboard:
        """Return the store's figures today. "This month" is the calendar month of today."""
        # Pending installments and unpaid statements due before today are the overdue ones.
        yesterday = today - timedelta(days=1)
        overdue = await self._credit.store_installments_due(store_id, FIRST_DAY, yesterday)
        overdue_cycles = await self._billing.store_cycles_due(store_id, FIRST_DAY, yesterday)
        purchases, payments = await self._totals(store_id, today.replace(day=1), today)
        return Dashboard(
            active_customers=await self._accounts.active_count(store_id),
            outstanding_principal=await self._credit.store_outstanding_principal(store_id),
            overdue_installments=len(overdue),
            overdue_statements=len(overdue_cycles),
            overdue_amount=sum((i.amount for i in overdue), ZERO)
            + sum((c.total for c in overdue_cycles), ZERO),
            purchases_this_month=purchases,
            payments_this_month=payments,
            bcrp_cap=await self._caps.in_force(today),
            upcoming=await self._upcoming(store_id, today),
            next_cutoff=await self._billing.next_cutoff(store_id),
        )

    async def period_report(self, store_id: int, from_date: date, to_date: date) -> PeriodReport:
        """Add up the purchases and payments made between the two days, both included."""
        if to_date < from_date:
            raise BusinessError(
                "INVALID_DATE_RANGE", "The end date must be on or after the start date.", field="to"
            )
        purchases, payments = await self._totals(store_id, from_date, to_date)
        return PeriodReport(from_date, to_date, purchases, payments)

    async def _upcoming(self, store_id: int, today: date) -> list[UpcomingDue]:
        """Installments and cycle statements falling due in the next 7 days, today included."""
        last_day = today + timedelta(days=UPCOMING_DAYS - 1)
        names = {
            holder.account_id: holder.full_name
            for holder in await self._accounts.holders_of_store(store_id)
        }
        installments = await self._credit.store_installments_due(store_id, today, last_day)
        cycles = await self._billing.store_cycles_due(store_id, today, last_day)
        dues = [
            UpcomingDue(INSTALLMENT, i.account_id, names[i.account_id], i.due_date, i.amount)
            for i in installments
        ] + [
            UpcomingDue(CYCLE, c.account_id, names[c.account_id], c.payment_date, c.total)
            for c in cycles
        ]
        return sorted(dues, key=lambda due: (due.due_date, due.type, due.account_id))

    async def _totals(
        self, store_id: int, from_date: date, to_date: date
    ) -> tuple[PurchaseTotals, PaymentTotals]:
        purchases = [
            purchase
            for purchase in await self._credit.store_purchases(store_id, from_date, to_date)
            # A voided purchase was registered by mistake: it was never a sale.
            if purchase.status != "VOIDED"
        ]
        payments = await self._billing.store_payments(store_id, from_date, to_date)
        purchase_totals = PurchaseTotals(
            count=len(purchases),
            amount=sum((p.amount for p in purchases), ZERO),
            ordinary_interest=sum((p.ordinary_interest for p in purchases), ZERO),
            single_date_count=sum(1 for p in purchases if p.mode == "SINGLE_DATE"),
            weekly_count=sum(1 for p in purchases if p.mode == "WEEKLY"),
        )
        payment_totals = PaymentTotals(
            count=len(payments),
            total=sum((p.total for p in payments), ZERO),
            principal=sum((p.principal for p in payments), ZERO),
            ordinary_interest=sum((p.ordinary_interest for p in payments), ZERO),
            late_interest=sum((p.late_interest for p in payments), ZERO),
            savings=sum((p.savings for p in payments), ZERO),
        )
        return purchase_totals, payment_totals
