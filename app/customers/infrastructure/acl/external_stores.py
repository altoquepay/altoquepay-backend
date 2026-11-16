from app.customers.application.ports.store_defaults import StoreDefaults
from app.shared.domain.value_objects import CreditConditions, Rate
from app.stores.interfaces.acl.stores_facade import StoresFacade


class ExternalStores(StoreDefaults):
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
