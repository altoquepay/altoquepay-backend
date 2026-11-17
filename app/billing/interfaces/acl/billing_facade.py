"""The only way other bounded contexts may reach the billing context."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.billing.application.command_services.billing_cycle_service import BillingCycleService
from app.billing.application.query_services.billing_query_service import BillingQueryService
from app.billing.domain.model.aggregates.payment import Payment
from app.billing.domain.repositories.payment_repository import PaymentFilter
from app.billing.infrastructure.acl.external_accounts import ExternalAccounts
from app.billing.infrastructure.acl.external_credit import ExternalCredit
from app.billing.infrastructure.persistence.billing_cycle_repository_impl import (
    BillingCycleRepositoryImpl,
)
from app.billing.infrastructure.persistence.payment_repository_impl import PaymentRepositoryImpl
from app.credit.interfaces.acl.credit_facade import CreditFacade
from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.shared.interfaces.rest.business_date import get_business_now, get_business_today


@dataclass(frozen=True)
class CycleReference:
    cycle_id: int
    year: int
    month: int
    cutoff_date: date
    payment_date: date


@dataclass(frozen=True)
class CycleStatement:
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


@dataclass(frozen=True)
class CycleDue:
    """A closed cycle whose statement is still to be paid on payment_date."""

    cycle_id: int
    account_id: int
    payment_date: date
    total: Decimal


@dataclass(frozen=True)
class PaymentSummary:
    payment_id: int
    kind: str
    paid_on: date
    late_interest: Decimal
    ordinary_interest: Decimal
    principal: Decimal
    total: Decimal
    savings: Decimal


class BillingFacade:
    """Never commits: the use case of the calling context does, once all its work succeeded."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        cycles = BillingCycleRepositoryImpl(unit_of_work.session)
        time_zone = ZoneInfo(get_settings().app_timezone)
        self._cycles = BillingCycleService(
            cycles, ExternalAccounts(CustomersFacade(unit_of_work)), time_zone
        )
        self._queries = BillingQueryService(
            cycles,
            PaymentRepositoryImpl(unit_of_work.session),
            ExternalCredit(CreditFacade(unit_of_work)),
        )

    async def get_or_open_cycle(self, account_id: int, purchased_at: datetime) -> CycleReference:
        """Return the cycle of a purchase by its cutoff date in Lima, creating it if needed.

        purchased_at must have a time zone. It flushes but does not commit. Raises NOT_FOUND
        (404) if the account does not exist and CYCLE_CLOSED (409) if the cycle is not open.
        """
        cycle = await self._cycles.get_or_open(account_id, purchased_at)
        if cycle.id is None:
            raise ValueError("The cycle was not stored.")
        return CycleReference(
            cycle.id, cycle.year, cycle.month, cycle.cutoff_date, cycle.payment_date
        )

    async def get_cycle_statement(
        self, account_id: int, year: int, month: int
    ) -> CycleStatement | None:
        """Return the statement of a month, or None if it has no cycle.

        The totals of an open cycle are calculated when queried, and an overdue cycle includes
        the late interest up to today. status may be OPEN, CLOSED, OVERDUE or PAID.
        """
        statement = await self._queries.get_statement(
            account_id, year, month, get_business_today(), get_business_now()
        )
        if statement is None:
            return None
        cycle = statement.cycle
        if cycle.id is None:
            raise ValueError("Only a stored cycle has a statement.")
        return CycleStatement(
            cycle_id=cycle.id,
            year=cycle.year,
            month=cycle.month,
            cutoff_date=cycle.cutoff_date,
            payment_date=cycle.payment_date,
            status=statement.status.value,
            capital=statement.totals.capital.amount,
            ordinary_interest=statement.totals.ordinary_interest.amount,
            late_interest=statement.late_interest.amount,
            total=statement.total.amount,
        )

    async def list_payments(self, account_id: int) -> list[PaymentSummary]:
        """Return the payments of an account, most recent first."""
        return [
            to_payment_summary(payment) for payment in await self._queries.list_payments(account_id)
        ]

    async def list_store_payments(
        self, store_id: int, from_date: date, to_date: date
    ) -> list[PaymentSummary]:
        """Return the store's payments made between the two days, most recent first."""
        payments = await self._queries.list_payments_of_store(
            store_id, PaymentFilter(from_date=from_date, to_date=to_date)
        )
        return [to_payment_summary(payment) for payment in payments]

    async def list_store_cycles_due(
        self, store_id: int, from_date: date, to_date: date
    ) -> list[CycleDue]:
        """Return the store's closed, unpaid cycles payable within the range, by payment date.

        Cycles whose cutoff already ended are closed first, as on every billing read.
        """
        cycles = await self._queries.list_cycles_due(
            store_id, from_date, to_date, get_business_today(), get_business_now()
        )
        return [
            CycleDue(cycle.id, cycle.store_customer_id, cycle.payment_date, cycle.total.amount)
            for cycle in cycles
            if cycle.id is not None and cycle.total is not None
        ]

    async def get_next_cutoff(self, store_id: int) -> date | None:
        """Return the earliest cutoff day, from today on, among the store's open cycles."""
        return await self._queries.next_cutoff(store_id, get_business_today())


def to_payment_summary(payment: Payment) -> PaymentSummary:
    if payment.id is None:
        raise ValueError("Only a stored payment has a summary.")
    breakdown = payment.breakdown
    return PaymentSummary(
        payment_id=payment.id,
        kind=payment.kind.value,
        paid_on=payment.paid_on,
        late_interest=breakdown.late_interest.amount,
        ordinary_interest=breakdown.ordinary_interest.amount,
        principal=breakdown.principal.amount,
        total=breakdown.total.amount,
        savings=breakdown.savings.amount,
    )
