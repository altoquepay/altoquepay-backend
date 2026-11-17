from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AccountInfo:
    store_id: int
    cutoff_day: int
    payment_day: int


@dataclass(frozen=True)
class AccountHolderInfo:
    dni: str
    full_name: str


class AccountDirectory(ABC):
    """What billing needs to know about accounts, answered by the customers context."""

    @abstractmethod
    async def get_account(self, account_id: int) -> AccountInfo:
        """Raise NOT_FOUND (404) if the account does not exist."""

    @abstractmethod
    async def lock(self, account_id: int) -> None:
        """Lock the account until the transaction ends, so two payments cannot cross."""

    @abstractmethod
    async def get_holder(self, account_id: int) -> AccountHolderInfo:
        """Return who holds the account, for its statement. Raise NOT_FOUND (404) if missing."""
