from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CycleDays:
    cutoff_day: int
    payment_day: int


class AccountDirectory(ABC):
    """What billing needs to know about accounts, answered by the customers context."""

    @abstractmethod
    async def get_cycle_days(self, account_id: int) -> CycleDays:
        """Raise NOT_FOUND (404) if the account does not exist."""
