"""The monthly cycle of an account: purchases until the cutoff, paid on the payment date."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.billing.domain.services.cycle_assignment import CyclePeriod
from app.shared.domain.value_objects import Money


class CycleStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


@dataclass
class BillingCycle:
    """Only an open cycle takes purchases. The totals are fixed when it closes."""

    store_customer_id: int
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
    def open(cls, account_id: int, period: CyclePeriod) -> "BillingCycle":
        return cls(account_id, period.year, period.month, period.cutoff_date, period.payment_date)

    @property
    def is_open(self) -> bool:
        return self.status == CycleStatus.OPEN
