from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.repositories.customer_repository import CustomerRepository
from app.customers.infrastructure.persistence.mappers import customer_to_model
from app.customers.infrastructure.persistence.models import CustomerModel


class CustomerRepositoryImpl(CustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_id_by_user(self, user_id: int) -> int | None:
        return await self._session.scalar(
            select(CustomerModel.id).where(CustomerModel.user_id == user_id)
        )

    async def add(self, customer: Customer) -> None:
        model = customer_to_model(customer)
        self._session.add(model)
        await self._session.flush()
        customer.id = model.id
