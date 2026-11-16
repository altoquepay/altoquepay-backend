"""The monthly cycle of an account: purchases until the cutoff, paid on the payment date."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from app.billing.domain.services.cycle_assignment import CyclePeriod
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money

ZERO = Money(Decimal(0))


class CycleStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PAID = "PAID"
    # Never stored: a closed cycle past its payment date is shown as overdue.
    OVERDUE = "OVERDUE"


@dataclass(frozen=True)
class StatementTotals:
    """What the single date purchases of a cycle owe: principal and their term interest."""

    capital: Money
    ordinary_interest: Money

    @property
    def total(self) -> Money:
        return Money(self.capital.amount + self.ordinary_interest.amount)


@dataclass
class BillingCycle:
    """Only an open cycle takes purchases. The totals are fixed when it closes.

    The statement holds the single date purchases; weekly ones are paid installment by
    installment, so they never add to it.
    """

    store_customer_id: int
    store_id: int
    year: int
    month: int
    cutoff_date: date
    payment_date: date
    status: CycleStatus = CycleStatus.OPEN
    closed_at: datetime | None = None
    capital: Money | None = None
    ordinary_interest: Money | None = None
    late_interest: Money | None = None
    total: Money | None = None
    id: int | None = None

    @classmethod
    def open(cls, account_id: int, store_id: int, period: CyclePeriod) -> "BillingCycle":
        return cls(
            account_id,
            store_id,
            period.year,
            period.month,
            period.cutoff_date,
            period.payment_date,
        )

    @property
    def is_open(self) -> bool:
        return self.status == CycleStatus.OPEN

    def is_due_for_closing(self, today: date) -> bool:
        """The cutoff day ends at midnight, so the cycle closes from the next day on."""
        return self.is_open and self.cutoff_date < today

    def status_on(self, today: date) -> CycleStatus:
        if self.status == CycleStatus.CLOSED and self.payment_date < today:
            return CycleStatus.OVERDUE
        return self.status

    def close(self, totals: StatementTotals, now: datetime) -> None:
        """Fix the statement. A cycle with nothing to pay is paid as soon as it closes."""
        self.capital = totals.capital
        self.ordinary_interest = totals.ordinary_interest
        self.late_interest = ZERO
        self.total = totals.total
        self.closed_at = now
        self.status = CycleStatus.PAID if totals.total.amount == 0 else CycleStatus.CLOSED

    def statement_totals(self) -> StatementTotals:
        if self.capital is None or self.ordinary_interest is None:
            raise ValueError("Only a closed cycle has fixed totals.")
        return StatementTotals(self.capital, self.ordinary_interest)

    def mark_paid(self, late_interest: Money) -> None:
        if self.status == CycleStatus.PAID:
            raise BusinessError("ALREADY_PAID", "It was already paid.", status=409)
        totals = self.statement_totals()
        self.late_interest = late_interest
        self.total = Money(totals.total.amount + late_interest.amount)
        self.status = CycleStatus.PAID
