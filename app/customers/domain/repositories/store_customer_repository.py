from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.model.aggregates.store_customer import AccountStatus, StoreCustomer


@dataclass(frozen=True)
class AccountFilter:
    """search matches part of the DNI or of the names, in any case."""

    search: str | None = None
    status: AccountStatus | None = None


class StoreCustomerRepository(ABC):
    @abstractmethod
    async def find_by_id(self, account_id: int) -> StoreCustomer | None: ...

    @abstractmethod
    async def find_by_store_and_customer(
        self, store_id: int, customer_id: int
    ) -> StoreCustomer | None: ...

    @abstractmethod
    async def lock(self, account_id: int) -> bool:
        """Lock the account until the transaction ends. Return False if it does not exist."""

    @abstractmethod
    async def list_by_customer(self, customer_id: int) -> list[StoreCustomer]:
        """Return the accounts of a person in every store, the oldest first."""

    @abstractmethod
    async def list_page(
        self, store_id: int, account_filter: AccountFilter, offset: int, size: int
    ) -> tuple[list[tuple[StoreCustomer, Customer]], int]:
        """Return a page of the store's accounts with their person, newest first, and the total."""

    @abstractmethod
    async def count_active_by_store(self, store_id: int) -> int: ...

    @abstractmethod
    async def add(self, account: StoreCustomer) -> None:
        """Store a new account and set its id and creation time."""

    @abstractmethod
    async def update(self, account: StoreCustomer) -> None:
        """Store the changes of an account that already has an id."""
