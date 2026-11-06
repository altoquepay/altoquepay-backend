"""The only way other bounded contexts may reach the catalog context."""

from dataclasses import dataclass
from decimal import Decimal

from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class ActiveProduct:
    product_id: int
    code: str
    description: str
    list_price: Decimal


class CatalogFacade:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def get_active_products(self, store_id: int, ids: list[int]) -> list[ActiveProduct]:
        """Return all the requested products of the store.

        Raises PRODUCT_NOT_AVAILABLE (422), with the ids in its details, if any of them is
        missing, inactive or from another store. Omitting it would register an incomplete sale.
        """
        raise NotImplementedError
