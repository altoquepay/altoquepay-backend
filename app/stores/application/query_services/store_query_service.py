from app.shared.domain.errors import BusinessError
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.repositories.store_repository import StoreRepository


class StoreQueryService:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def get(self, store_id: int) -> Store:
        store = await self._stores.find_by_id(store_id)
        if store is None:
            raise BusinessError("NOT_FOUND", "The store does not exist.", status=404)
        return store
