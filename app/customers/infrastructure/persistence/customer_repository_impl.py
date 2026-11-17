from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.repositories.customer_repository import CustomerRepository
from app.customers.infrastructure.persistence.mappers import (
    copy_customer_to_model,
    customer_to_domain,
)
from app.customers.infrastructure.persistence.models import CustomerModel
from app.shared.domain.value_objects import Dni


class CustomerRepositoryImpl(CustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, customer_id: int) -> Customer | None:
        model = await self._session.get(CustomerModel, customer_id)
        return customer_to_domain(model) if model else None

    async def find_by_dni(self, dni: Dni) -> Customer | None:
        model = await self._session.scalar(
            select(CustomerModel).where(CustomerModel.dni == dni.value)
        )
        return customer_to_domain(model) if model else None

    async def find_id_by_user(self, user_id: int) -> int | None:
        return await self._session.scalar(
            select(CustomerModel.id).where(CustomerModel.user_id == user_id)
        )

    async def add(self, customer: Customer) -> None:
        model = copy_customer_to_model(customer, CustomerModel())
        self._session.add(model)
        await self._session.flush()
        customer.id = model.id
