from app.catalog.domain.model.aggregates.product import Product
from app.catalog.domain.repositories.product_repository import ProductFilter, ProductRepository
from app.shared.domain.errors import BusinessError


class ProductQueryService:
    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    async def get(self, store_id: int, product_id: int) -> Product:
        """Raise NOT_FOUND (404) for a product of another store, as if it did not exist."""
        product = await self._products.find_by_id(product_id)
        if product is None or product.store_id != store_id:
            raise BusinessError("NOT_FOUND", "The product does not exist.", status=404)
        return product

    async def list_page(
        self, store_id: int, product_filter: ProductFilter, offset: int, size: int
    ) -> tuple[list[Product], int]:
        return await self._products.list_page(store_id, product_filter, offset, size)
