from abc import ABC, abstractmethod

from app.shared.domain.value_objects import Ruc
from app.stores.domain.model.aggregates.store import Store


class StoreRepository(ABC):
    @abstractmethod
    async def find_by_id(self, store_id: int) -> Store | None: ...

    @abstractmethod
    async def exists_by_ruc(self, ruc: Ruc) -> bool: ...

    @abstractmethod
    async def list_page(self, offset: int, size: int) -> tuple[list[Store], int]:
        """Return a page of stores, the most recently registered first, and the total count."""

    @abstractmethod
    async def add(self, store: Store) -> None:
        """Store a new store and set its id and registration time."""

    @abstractmethod
    async def update(self, store: Store) -> None: ...
