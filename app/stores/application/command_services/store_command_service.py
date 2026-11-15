from datetime import date

from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.stores.application.ports.rate_cap_checker import RateCapChecker
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.model.commands.update_store_profile_command import (
    UpdateStoreProfileCommand,
)
from app.stores.domain.repositories.store_repository import StoreRepository


class StoreCommandService:
    def __init__(
        self, stores: StoreRepository, rate_caps: RateCapChecker, unit_of_work: UnitOfWork
    ) -> None:
        self._stores = stores
        self._rate_caps = rate_caps
        self._unit_of_work = unit_of_work

    async def update_profile(self, command: UpdateStoreProfileCommand, today: date) -> Store:
        """Save the profile once its default rates respect the BCRP caps in force today."""
        store = await self._find(command.store_id)
        conditions = command.default_conditions
        await self._rate_caps.check(conditions.tea, conditions.late_tea, today)
        store.update_profile(command.business_name, command.address, command.phone, conditions)
        await self._stores.update(store)
        await self._unit_of_work.commit()
        return store

    async def _find(self, store_id: int) -> Store:
        store = await self._stores.find_by_id(store_id)
        if store is None:
            raise BusinessError("NOT_FOUND", "The store does not exist.", status=404)
        return store
