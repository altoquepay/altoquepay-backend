"""The store administrator's dashboard and period report, added up account by account."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.credit.interfaces.acl.credit_facade import PurchaseSummary
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
class Dashboard:
    active_customers: int
    outstanding_principal: Decimal
    overdue_installments: int
    overdue_amount: Decimal
    purchases_this_month: PurchaseTotals
    payments_this_month: PaymentTotals
    bcrp_cap: CurrentCap | None


@dataclass(frozen=True)
class PeriodReport:
    from_date: date
    to_date: date
    purchases: PurchaseTotals
    payments: PaymentTotals


class StoreReportService:
    """shortcut: it reads every account of the store through the facades, one at a time. That
    is fine for a bodega's few hundred customers; add store-wide facade methods if it slows down.
    """

    def __init__(
        self,
        accounts: CustomerAccounts,
        credit: CreditReader,
        billing: BillingReader,
        caps: RateCaps,
        business_time_zone: ZoneInfo,
    ) -> None:
        self._accounts = accounts
        self._credit = credit
        self._billing = billing
        self._caps = caps
        self._business_time_zone = business_time_zone

    async def dashboard(self, store_id: int, today: date) -> Dashboard:
        """Return the store's figures today. "This month" is the calendar month of today."""
        month_start = today.replace(day=1)
        outstanding = ZERO
        overdue_count, overdue_amount = 0, ZERO
        account_ids = await self._account_ids(store_id)
        for account_id in account_ids:
            outstanding += await self._credit.outstanding_principal(account_id)
            # Pending installments due before today are the overdue ones.
            overdue = await self._credit.installments_due(
                account_id, FIRST_DAY, today - timedelta(days=1)
            )
            overdue_count += len(overdue)
            overdue_amount += sum((i.amount for i in overdue), ZERO)
        purchases, payments = await self._totals(account_ids, month_start, today)
        return Dashboard(
            active_customers=await self._accounts.active_count(store_id),
            outstanding_principal=outstanding,
            overdue_installments=overdue_count,
            overdue_amount=overdue_amount,
            purchases_this_month=purchases,
            payments_this_month=payments,
            bcrp_cap=await self._caps.in_force(today),
        )

    async def period_report(self, store_id: int, from_date: date, to_date: date) -> PeriodReport:
        """Add up the purchases and payments made between the two days, both included."""
        if to_date < from_date:
            raise BusinessError(
                "INVALID_DATE_RANGE", "The end date must be on or after the start date.", field="to"
            )
        purchases, payments = await self._totals(
            await self._account_ids(store_id), from_date, to_date
        )
        return PeriodReport(from_date, to_date, purchases, payments)

    async def _account_ids(self, store_id: int) -> list[int]:
        return [account.account_id for account in await self._accounts.accounts_of_store(store_id)]

    async def _totals(
        self, account_ids: list[int], from_date: date, to_date: date
    ) -> tuple[PurchaseTotals, PaymentTotals]:
        purchases: list[PurchaseSummary] = []
        payments = []
        for account_id in account_ids:
            purchases += [
                p
                for p in await self._credit.purchases(account_id)
                if from_date <= self._day_of(p) <= to_date
            ]
            payments += [
                p
                for p in await self._billing.payments(account_id)
                if from_date <= p.paid_on <= to_date
            ]
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

    def _day_of(self, purchase: PurchaseSummary) -> date:
        return purchase.purchased_at.astimezone(self._business_time_zone).date()
