from app.customers.application.ports.store_directory import StoreDirectory
from app.shared.domain.value_objects import CreditConditions, Rate
from app.stores.interfaces.acl.stores_facade import StoresFacade

ACTIVE_STORE_STATUS = "ACTIVE"


class ExternalStores(StoreDirectory):
    def __init__(self, stores_facade: StoresFacade) -> None:
        self._stores_facade = stores_facade

    async def get(self, store_id: int) -> CreditConditions:
        defaults = await self._stores_facade.get_default_conditions(store_id)
        return CreditConditions(
            cutoff_day=defaults.cutoff_day,
            payment_day=defaults.payment_day,
            tea=Rate.from_percent(defaults.tea),
            late_tea=Rate.from_percent(defaults.late_tea),
            max_weeks=defaults.max_weeks,
        )

    async def is_store_active(self, store_id: int) -> bool:
        store = await self._stores_facade.get_store_status(store_id)
        return store.status == ACTIVE_STORE_STATUS
