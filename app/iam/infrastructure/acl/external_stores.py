from app.iam.application.ports.store_directory import StoreDirectory
from app.stores.interfaces.acl.stores_facade import StoresFacade

ACTIVE_STORE_STATUS = "ACTIVE"


class ExternalStores(StoreDirectory):
    def __init__(self, stores_facade: StoresFacade) -> None:
        self._stores_facade = stores_facade

    async def is_store_active(self, store_id: int) -> bool:
        store = await self._stores_facade.get_store_status(store_id)
        return store.status == ACTIVE_STORE_STATUS
