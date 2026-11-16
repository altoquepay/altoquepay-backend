from abc import ABC, abstractmethod

from app.catalog.domain.model.aggregates.product import Product


class ProductRepository(ABC):
    @abstractmethod
    async def find_active(self, store_id: int, ids: set[int]) -> list[Product]:
        """Return the active products of the store among the given ids, in one query."""

    @abstractmethod
    async def add(self, product: Product) -> None:
        """Store a new product and set its id."""
