from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from app.billing.domain.model.aggregates.billing_cycle import BillingCycle, CycleStatus


@dataclass(frozen=True)
class CycleFilter:
    """status may be OVERDUE, which matches closed cycles past their payment date."""

    year: int | None = None
    month: int | None = None
    status: CycleStatus | None = None
    account_id: int | None = None


class BillingCycleRepository(ABC):
    @abstractmethod
    async def find_by_id(self, cycle_id: int, *, for_update: bool = False) -> BillingCycle | None:
        """for_update locks the cycle until the transaction ends, so closing it waits."""

    @abstractmethod
    async def find(
        self, account_id: int, year: int, month: int, *, for_update: bool = False
    ) -> BillingCycle | None:
        """for_update locks the cycle until the transaction ends, so closing it waits."""

    @abstractmethod
    async def list_due_for_closing(
        self, today: date, *, store_id: int | None = None, account_id: int | None = None
    ) -> list[BillingCycle]:
        """Return the open cycles whose cutoff day already ended, of a store or an account."""

    @abstractmethod
    async def list_closed_by_payment_date(
        self, store_id: int, from_date: date, to_date: date
    ) -> list[BillingCycle]:
        """Return the store's closed, unpaid cycles payable within the inclusive range."""

    @abstractmethod
    async def find_next_cutoff(self, store_id: int, today: date) -> date | None:
        """Return the earliest cutoff day, today or later, among the store's open cycles."""

    @abstractmethod
    async def list_page(
        self, store_id: int, cycle_filter: CycleFilter, today: date, offset: int, size: int
    ) -> tuple[list[BillingCycle], int]:
        """Return a page of the store's cycles, the most recent period first, and the total."""

    @abstractmethod
    async def add(self, cycle: BillingCycle) -> None:
        """Store a new cycle and set its id."""

    @abstractmethod
    async def update(self, cycle: BillingCycle) -> None:
        """Store the changes of a cycle that already has an id."""
