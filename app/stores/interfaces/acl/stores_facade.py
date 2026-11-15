"""The only way other bounded contexts may reach the stores context.

Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.stores.domain.model.aggregates.store import Store
from app.stores.infrastructure.persistence.store_repository_impl import StoreRepositoryImpl


@dataclass(frozen=True)
class StoreSummary:
    store_id: int
    business_name: str
    status: str


@dataclass(frozen=True)
class DefaultConditions:
    cutoff_day: int
    payment_day: int
    tea: Decimal
    late_tea: Decimal
    max_weeks: int


class StoresFacade:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        # The repository, not StoreQueryService: that service needs the customers facade, and
        # customers will ask this facade for default conditions, which would be an import cycle.
        self._stores = StoreRepositoryImpl(unit_of_work.session)

    async def get_store_status(self, store_id: int) -> StoreSummary:
        """Return the status of a store, with the name its customers see in their portal."""
        store = await self._find(store_id)
        return StoreSummary(store_id, store.business_name, store.status.value)

    async def get_default_conditions(self, store_id: int) -> DefaultConditions:
        """Return the conditions a new customer gets when the store sets none."""
        conditions = (await self._find(store_id)).default_conditions
        return DefaultConditions(
            cutoff_day=conditions.cutoff_day,
            payment_day=conditions.payment_day,
            tea=conditions.tea.percent,
            late_tea=conditions.late_tea.percent,
            max_weeks=conditions.max_weeks,
        )

    async def _find(self, store_id: int) -> Store:
        """Raise NOT_FOUND (404) if the store does not exist."""
        store = await self._stores.find_by_id(store_id)
        if store is None:
            raise BusinessError("NOT_FOUND", "The store does not exist.", status=404)
        return store
