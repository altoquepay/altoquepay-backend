from abc import ABC, abstractmethod

from app.billing.domain.model.aggregates.billing_cycle import BillingCycle


class BillingCycleRepository(ABC):
    @abstractmethod
    async def find(self, account_id: int, year: int, month: int) -> BillingCycle | None: ...

    @abstractmethod
    async def add(self, cycle: BillingCycle) -> None:
        """Store a new cycle and set its id."""
