from dataclasses import dataclass

from app.shared.domain.errors import BusinessError
from app.stores.application.ports.customer_counter import CustomerCounter
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.repositories.store_repository import StoreRepository


@dataclass(frozen=True)
class StoreWithCustomers:
    store: Store
    customers_count: int


class StoreQueryService:
    def __init__(self, stores: StoreRepository, customers: CustomerCounter) -> None:
        self._stores = stores
        self._customers = customers

    async def get(self, store_id: int) -> Store:
        store = await self._stores.find_by_id(store_id)
        if store is None:
            raise BusinessError("NOT_FOUND", "The store does not exist.", status=404)
        return store

    async def list_page(self, offset: int, size: int) -> tuple[list[StoreWithCustomers], int]:
        """Return a page of stores, the most recently registered first, and the total count."""
        stores, total = await self._stores.list_page(offset, size)
        # One count per store is fine: a page holds at most 100 stores.
        listed = [
            StoreWithCustomers(store, await self._customers.count(store.id or 0))
            for store in stores
        ]
        return listed, total
