from abc import ABC, abstractmethod

from app.shared.domain.value_objects import Money


class ProductPrices(ABC):
    """The list prices of the store's products, answered by the catalog context."""

    @abstractmethod
    async def list_prices(self, store_id: int, product_ids: list[int]) -> dict[int, Money]:
        """Return the list price of every product. Raises PRODUCT_NOT_AVAILABLE if one is not."""
