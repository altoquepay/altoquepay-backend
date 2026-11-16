from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.domain.model.aggregates.billing_cycle import BillingCycle
from app.billing.domain.repositories.billing_cycle_repository import BillingCycleRepository
from app.billing.infrastructure.persistence.mappers import to_domain, to_model
from app.billing.infrastructure.persistence.models import BillingCycleModel


class BillingCycleRepositoryImpl(BillingCycleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, account_id: int, year: int, month: int) -> BillingCycle | None:
        model = await self._session.scalar(
            select(BillingCycleModel).where(
                BillingCycleModel.store_customer_id == account_id,
                BillingCycleModel.year == year,
                BillingCycleModel.month == month,
            )
        )
        return to_domain(model) if model else None

    async def add(self, cycle: BillingCycle) -> None:
        model = to_model(cycle)
        self._session.add(model)
        await self._session.flush()
        cycle.id = model.id
