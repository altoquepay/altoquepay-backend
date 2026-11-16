from abc import ABC, abstractmethod

from app.customers.domain.model.aggregates.store_customer import StoreCustomer


class StoreCustomerRepository(ABC):
    @abstractmethod
    async def find_by_id(self, account_id: int) -> StoreCustomer | None: ...

    @abstractmethod
    async def lock(self, account_id: int) -> bool:
        """Lock the account until the transaction ends. Return False if it does not exist."""

    @abstractmethod
    async def list_by_customer(self, customer_id: int) -> list[StoreCustomer]:
        """Return the accounts of a person in every store, the oldest first."""

    @abstractmethod
    async def count_active_by_store(self, store_id: int) -> int: ...

    @abstractmethod
    async def add(self, account: StoreCustomer) -> None:
        """Store a new account and set its id and creation time."""
