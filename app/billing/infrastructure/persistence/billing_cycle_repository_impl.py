from datetime import date

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.domain.model.aggregates.billing_cycle import BillingCycle, CycleStatus
from app.billing.domain.repositories.billing_cycle_repository import (
    BillingCycleRepository,
    CycleFilter,
)
from app.billing.infrastructure.persistence.mappers import copy_to_model, to_domain
from app.billing.infrastructure.persistence.models import BillingCycleModel


def filtered(query: Select, store_id: int, cycle_filter: CycleFilter, today: date) -> Select:
    query = query.where(BillingCycleModel.store_id == store_id)
    if cycle_filter.year is not None:
        query = query.where(BillingCycleModel.year == cycle_filter.year)
    if cycle_filter.month is not None:
        query = query.where(BillingCycleModel.month == cycle_filter.month)
    if cycle_filter.account_id is not None:
        query = query.where(BillingCycleModel.store_customer_id == cycle_filter.account_id)
    closed = BillingCycleModel.status == CycleStatus.CLOSED.value
    # OVERDUE is never stored: it is a closed cycle past its payment date.
    if cycle_filter.status == CycleStatus.OVERDUE:
        query = query.where(and_(closed, BillingCycleModel.payment_date < today))
    elif cycle_filter.status == CycleStatus.CLOSED:
        query = query.where(and_(closed, BillingCycleModel.payment_date >= today))
    elif cycle_filter.status is not None:
        query = query.where(BillingCycleModel.status == cycle_filter.status.value)
    return query


class BillingCycleRepositoryImpl(BillingCycleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, cycle_id: int) -> BillingCycle | None:
        model = await self._session.get(BillingCycleModel, cycle_id)
        return to_domain(model) if model else None

    async def find(self, account_id: int, year: int, month: int) -> BillingCycle | None:
        model = await self._session.scalar(
            select(BillingCycleModel).where(
                BillingCycleModel.store_customer_id == account_id,
                BillingCycleModel.year == year,
                BillingCycleModel.month == month,
            )
        )
        return to_domain(model) if model else None

    async def list_due_for_closing(
        self, today: date, *, store_id: int | None = None, account_id: int | None = None
    ) -> list[BillingCycle]:
        query = select(BillingCycleModel).where(
            BillingCycleModel.status == CycleStatus.OPEN.value,
            BillingCycleModel.cutoff_date < today,
        )
        if store_id is not None:
            query = query.where(BillingCycleModel.store_id == store_id)
        if account_id is not None:
            query = query.where(BillingCycleModel.store_customer_id == account_id)
        # Locked in id order, so a payment cannot pay a cycle that this read is closing.
        models = await self._session.scalars(query.order_by(BillingCycleModel.id).with_for_update())
        return [to_domain(model) for model in models]

    async def list_closed_by_payment_date(
        self, store_id: int, from_date: date, to_date: date
    ) -> list[BillingCycle]:
        models = await self._session.scalars(
            select(BillingCycleModel)
            .where(
                BillingCycleModel.store_id == store_id,
                BillingCycleModel.status == CycleStatus.CLOSED.value,
                BillingCycleModel.payment_date.between(from_date, to_date),
            )
            .order_by(BillingCycleModel.payment_date, BillingCycleModel.id)
        )
        return [to_domain(model) for model in models]

    async def find_next_cutoff(self, store_id: int, today: date) -> date | None:
        return await self._session.scalar(
            select(func.min(BillingCycleModel.cutoff_date)).where(
                BillingCycleModel.store_id == store_id,
                BillingCycleModel.status == CycleStatus.OPEN.value,
                BillingCycleModel.cutoff_date >= today,
            )
        )

    async def list_page(
        self, store_id: int, cycle_filter: CycleFilter, today: date, offset: int, size: int
    ) -> tuple[list[BillingCycle], int]:
        total = await self._session.scalar(
            filtered(
                select(func.count()).select_from(BillingCycleModel), store_id, cycle_filter, today
            )
        )
        models = await self._session.scalars(
            filtered(select(BillingCycleModel), store_id, cycle_filter, today)
            .order_by(
                BillingCycleModel.year.desc(),
                BillingCycleModel.month.desc(),
                BillingCycleModel.id.desc(),
            )
            .offset(offset)
            .limit(size)
        )
        return [to_domain(model) for model in models], total or 0

    async def add(self, cycle: BillingCycle) -> None:
        model = copy_to_model(cycle, BillingCycleModel())
        self._session.add(model)
        await self._session.flush()
        cycle.id = model.id

    async def update(self, cycle: BillingCycle) -> None:
        if cycle.id is None:
            raise ValueError("Only a stored cycle can be updated.")
        model = await self._session.get_one(BillingCycleModel, cycle.id)
        copy_to_model(cycle, model)
        await self._session.flush()
