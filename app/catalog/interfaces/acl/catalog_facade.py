"""The only way other bounded contexts may reach the catalog context."""

from dataclasses import dataclass
from decimal import Decimal

from app.catalog.infrastructure.persistence.product_repository_impl import ProductRepositoryImpl
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class ActiveProduct:
    product_id: int
    code: str
    description: str
    list_price: Decimal


class CatalogFacade:
    """Never commits. Unlike the other facades, it filters by store: products are per store."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._products = ProductRepositoryImpl(unit_of_work.session)

    async def get_active_products(self, store_id: int, ids: list[int]) -> list[ActiveProduct]:
        """Return all the requested products of the store, in no particular order.

        Raises PRODUCT_NOT_AVAILABLE (422), with the ids in its details, if any of them is
        missing, inactive or from another store. Omitting it would register an incomplete sale.
        """
        requested_ids = set(ids)
        products = await self._products.find_active(store_id, requested_ids)
        missing_ids = sorted(requested_ids - {product.id for product in products})
        if missing_ids:
            raise BusinessError(
                "PRODUCT_NOT_AVAILABLE",
                "Some products do not exist, are inactive or belong to another store.",
                field="items",
                details={"product_ids": missing_ids},  # type: ignore[dict-item]
            )
        return [
            ActiveProduct(product.id, product.code, product.description, product.list_price.amount)
            for product in products
            if product.id is not None
        ]
