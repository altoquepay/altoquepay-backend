from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customers.domain.model.aggregates.store_customer import AccountStatus, StoreCustomer
from app.customers.domain.repositories.store_customer_repository import StoreCustomerRepository
from app.customers.infrastructure.persistence.mappers import account_to_domain, account_to_model
from app.customers.infrastructure.persistence.models import StoreCustomerModel


class StoreCustomerRepositoryImpl(StoreCustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, account_id: int) -> StoreCustomer | None:
        model = await self._session.get(StoreCustomerModel, account_id)
        return account_to_domain(model) if model else None

    async def lock(self, account_id: int) -> bool:
        locked_id = await self._session.scalar(
            select(StoreCustomerModel.id)
            .where(StoreCustomerModel.id == account_id)
            .with_for_update()
        )
        return locked_id is not None

    async def list_by_customer(self, customer_id: int) -> list[StoreCustomer]:
        models = await self._session.scalars(
            select(StoreCustomerModel)
            .where(StoreCustomerModel.customer_id == customer_id)
            .order_by(StoreCustomerModel.id)
        )
        return [account_to_domain(model) for model in models]

    async def count_active_by_store(self, store_id: int) -> int:
        count = await self._session.scalar(
            select(func.count()).where(
                StoreCustomerModel.store_id == store_id,
                StoreCustomerModel.status == AccountStatus.ACTIVE.value,
            )
        )
        return count or 0

    async def add(self, account: StoreCustomer) -> None:
        model = account_to_model(account)
        self._session.add(model)
        await self._session.flush()
        # The database sets the creation time, so read it back.
        await self._session.refresh(model, ["created_at"])
        account.id = model.id
        account.created_at = model.created_at
