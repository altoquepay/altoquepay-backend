from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.catalog.domain.model.aggregates.product import Product


@dataclass(frozen=True)
class ProductFilter:
    """search matches part of the code or of the description, in any case."""

    search: str | None = None
    active: bool | None = None


class ProductRepository(ABC):
    @abstractmethod
    async def find_by_id(self, product_id: int) -> Product | None: ...

    @abstractmethod
    async def find_active(self, store_id: int, ids: set[int]) -> list[Product]:
        """Return the active products of the store among the given ids, in one query."""

    @abstractmethod
    async def code_taken(self, store_id: int, code: str, except_id: int | None = None) -> bool:
        """Whether another product of the store already has this code."""

    @abstractmethod
    async def list_page(
        self, store_id: int, product_filter: ProductFilter, offset: int, size: int
    ) -> tuple[list[Product], int]:
        """Return a page of the store's products by code, and the total count."""

    @abstractmethod
    async def add(self, product: Product) -> None:
        """Store a new product and set its id."""

    @abstractmethod
    async def update(self, product: Product) -> None:
        """Store the changes of a product that already has an id."""
