"""The only way other bounded contexts may reach the billing context."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.billing.application.command_services.billing_cycle_service import BillingCycleService
from app.billing.infrastructure.acl.external_accounts import ExternalAccounts
from app.billing.infrastructure.persistence.billing_cycle_repository_impl import (
    BillingCycleRepositoryImpl,
)
from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.unit_of_work import UnitOfWork


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
        self._unit_of_work = unit_of_work
        self._cycles = BillingCycleService(
            BillingCycleRepositoryImpl(unit_of_work.session),
            ExternalAccounts(CustomersFacade(unit_of_work)),
            ZoneInfo(get_settings().app_timezone),
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

        The totals of an open cycle are calculated when queried.
        """
        raise NotImplementedError

    async def list_payments(self, account_id: int) -> list[PaymentSummary]:
        """Return the payments of an account, most recent first."""
        raise NotImplementedError
