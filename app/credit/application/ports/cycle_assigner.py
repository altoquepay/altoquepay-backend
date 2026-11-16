from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class AssignedCycle:
    cycle_id: int
    payment_date: date


class CycleAssigner(ABC):
    """The monthly cycle of a purchase, answered by the billing context."""

    @abstractmethod
    async def cycle_of(self, account_id: int, purchased_at: datetime) -> AssignedCycle:
        """Return the open cycle of the purchase, creating it if needed, without committing.

        Raises CYCLE_CLOSED (409) if that cycle is already closed.
        """
