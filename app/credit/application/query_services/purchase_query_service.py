from datetime import date

from app.credit.domain.model.aggregates.purchase import InstallmentStatus, Purchase
from app.credit.domain.repositories.purchase_repository import (
    InstallmentEntry,
    PurchaseFilter,
    PurchaseRepository,
)
from app.shared.domain.errors import BusinessError


class PurchaseQueryService:
    def __init__(self, purchases: PurchaseRepository) -> None:
        self._purchases = purchases

    async def get(self, store_id: int, purchase_id: int) -> Purchase:
        """Return a purchase of the store. Another store's purchase is NOT_FOUND, as if missing."""
        purchase = await self._purchases.find_by_id(purchase_id)
        if purchase is None or purchase.store_id != store_id:
            raise BusinessError("NOT_FOUND", "The purchase does not exist.", status=404)
        return purchase

    async def list_page(
        self, store_id: int, purchase_filter: PurchaseFilter, offset: int, size: int
    ) -> tuple[list[Purchase], int]:
        return await self._purchases.list_page(store_id, purchase_filter, offset, size)

    async def list_installments(
        self,
        store_id: int,
        status: InstallmentStatus | None,
        due_before: date | None,
        today: date,
        offset: int,
        size: int,
    ) -> tuple[list[InstallmentEntry], int]:
        return await self._purchases.list_installments(
            store_id, status, due_before, today, offset, size
        )
