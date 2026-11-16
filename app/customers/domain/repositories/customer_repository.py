from abc import ABC, abstractmethod

from app.customers.domain.model.aggregates.customer import Customer
from app.shared.domain.value_objects import Dni


class CustomerRepository(ABC):
    @abstractmethod
    async def find_by_id(self, customer_id: int) -> Customer | None: ...

    @abstractmethod
    async def find_by_dni(self, dni: Dni) -> Customer | None: ...

    @abstractmethod
    async def find_id_by_user(self, user_id: int) -> int | None: ...

    @abstractmethod
    async def add(self, customer: Customer) -> None:
        """Store a new customer and set its id."""

    @abstractmethod
    async def update(self, customer: Customer) -> None:
        """Store the changes of a customer that already has an id."""
