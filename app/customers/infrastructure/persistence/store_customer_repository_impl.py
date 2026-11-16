from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.model.aggregates.store_customer import AccountStatus, StoreCustomer
from app.customers.domain.repositories.store_customer_repository import (
    AccountFilter,
    StoreCustomerRepository,
)
from app.customers.infrastructure.persistence.mappers import (
    account_to_domain,
    copy_account_to_model,
    customer_to_domain,
)
from app.customers.infrastructure.persistence.models import CustomerModel, StoreCustomerModel


def escape_like(text: str) -> str:
    """Make % and _ in a search match themselves instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def filtered(query: Select, store_id: int, account_filter: AccountFilter) -> Select:
    query = query.where(StoreCustomerModel.store_id == store_id)
    if account_filter.status is not None:
        query = query.where(StoreCustomerModel.status == account_filter.status.value)
    search = (account_filter.search or "").strip()
    if search:
        pattern = f"%{escape_like(search)}%"
        full_name = CustomerModel.first_names + " " + CustomerModel.last_names
        query = query.where(
            or_(
                CustomerModel.dni.ilike(pattern, escape="\\"),
                full_name.ilike(pattern, escape="\\"),
            )
        )
    return query


class StoreCustomerRepositoryImpl(StoreCustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, account_id: int) -> StoreCustomer | None:
        model = await self._session.get(StoreCustomerModel, account_id)
        return account_to_domain(model) if model else None

    async def find_by_store_and_customer(
        self, store_id: int, customer_id: int
    ) -> StoreCustomer | None:
        model = await self._session.scalar(
            select(StoreCustomerModel).where(
                StoreCustomerModel.store_id == store_id,
                StoreCustomerModel.customer_id == customer_id,
            )
        )
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

    async def list_by_store(self, store_id: int) -> list[StoreCustomer]:
        models = await self._session.scalars(
            select(StoreCustomerModel)
            .where(StoreCustomerModel.store_id == store_id)
            .order_by(StoreCustomerModel.id)
        )
        return [account_to_domain(model) for model in models]

    async def list_page(
        self, store_id: int, account_filter: AccountFilter, offset: int, size: int
    ) -> tuple[list[tuple[StoreCustomer, Customer]], int]:
        joined = select(StoreCustomerModel, CustomerModel).join(
            CustomerModel, CustomerModel.id == StoreCustomerModel.customer_id
        )
        counted = (
            select(func.count())
            .select_from(StoreCustomerModel)
            .join(CustomerModel, CustomerModel.id == StoreCustomerModel.customer_id)
        )
        total = await self._session.scalar(filtered(counted, store_id, account_filter))
        rows = await self._session.execute(
            filtered(joined, store_id, account_filter)
            .order_by(StoreCustomerModel.created_at.desc(), StoreCustomerModel.id.desc())
            .offset(offset)
            .limit(size)
        )
        listed = [
            (account_to_domain(account), customer_to_domain(person)) for account, person in rows
        ]
        return listed, total or 0

    async def count_active_by_store(self, store_id: int) -> int:
        count = await self._session.scalar(
            select(func.count()).where(
                StoreCustomerModel.store_id == store_id,
                StoreCustomerModel.status == AccountStatus.ACTIVE.value,
            )
        )
        return count or 0

    async def add(self, account: StoreCustomer) -> None:
        model = copy_account_to_model(account, StoreCustomerModel())
        self._session.add(model)
        await self._session.flush()
        # The database sets the creation time, so read it back.
        await self._session.refresh(model, ["created_at"])
        account.id = model.id
        account.created_at = model.created_at

    async def update(self, account: StoreCustomer) -> None:
        if account.id is None:
            raise ValueError("Only a stored account can be updated.")
        model = await self._session.get_one(StoreCustomerModel, account.id)
        copy_account_to_model(account, model)
        await self._session.flush()
