from app.catalog.interfaces.acl.catalog_facade import CatalogFacade
from app.credit.application.ports.product_prices import ProductPrices
from app.shared.domain.value_objects import Money


class ExternalCatalog(ProductPrices):
    def __init__(self, catalog_facade: CatalogFacade) -> None:
        self._catalog_facade = catalog_facade

    async def list_prices(self, store_id: int, product_ids: list[int]) -> dict[int, Money]:
        products = await self._catalog_facade.get_active_products(store_id, product_ids)
        return {product.product_id: Money(product.list_price) for product in products}
