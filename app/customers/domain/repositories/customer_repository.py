from abc import ABC, abstractmethod

from app.customers.domain.model.aggregates.customer import Customer


class CustomerRepository(ABC):
    @abstractmethod
    async def find_id_by_user(self, user_id: int) -> int | None: ...

    @abstractmethod
    async def add(self, customer: Customer) -> None:
        """Store a new customer and set its id."""
