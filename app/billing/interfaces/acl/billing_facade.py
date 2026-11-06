"""The only way other bounded contexts may reach the billing context."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

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
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def get_or_open_cycle(self, account_id: int, purchased_at: datetime) -> CycleReference:
        """Return the cycle of a purchase by its cutoff date in Lima, creating it if needed.

        It flushes but does not commit. Raises CYCLE_CLOSED (409) if the cycle is already closed.
        """
        raise NotImplementedError

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
