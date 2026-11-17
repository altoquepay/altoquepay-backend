from app.billing.application.ports.store_directory import StoreDirectory
from app.stores.interfaces.acl.stores_facade import StoresFacade


class ExternalStores(StoreDirectory):
    def __init__(self, stores_facade: StoresFacade) -> None:
        self._stores_facade = stores_facade

    async def business_name(self, store_id: int) -> str:
        return (await self._stores_facade.get_store_status(store_id)).business_name
