from datetime import datetime
from decimal import Decimal

from app.credit.application.ports.credit_accounts import CreditAccounts
from app.credit.application.ports.cycle_assigner import CycleAssigner
from app.credit.application.ports.product_prices import ProductPrices
from app.credit.domain.model.aggregates.purchase import (
    Purchase,
    PurchaseItem,
    outstanding_principal_of,
)
from app.credit.domain.model.commands.register_purchase_command import RegisterPurchaseCommand
from app.credit.domain.repositories.purchase_repository import PurchaseRepository
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork


class PurchaseRegistrationService:
    def __init__(
        self,
        purchases: PurchaseRepository,
        accounts: CreditAccounts,
        prices: ProductPrices,
        cycles: CycleAssigner,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._purchases = purchases
        self._accounts = accounts
        self._prices = prices
        self._cycles = cycles
        self._unit_of_work = unit_of_work

    async def simulate(self, command: RegisterPurchaseCommand, now: datetime) -> Purchase:
        """Calculate the purchase without saving it. now is in the business time zone.

        A cycle that billing opens here is discarded, because nothing is committed.
        """
        terms = await self._accounts.lock_and_read(command.account_id)
        if terms.store_id != command.store_id:
            # Same answer as a missing account, so other stores' customers stay hidden.
            raise BusinessError("NOT_FOUND", "The customer does not exist.", status=404)
        if not terms.is_active:
            raise BusinessError(
                "ACCOUNT_INACTIVE", "This customer can no longer buy on credit.", status=409
            )
        if command.purchased_at > now:
            raise BusinessError(
                "PURCHASE_IN_FUTURE", "A purchase cannot be in the future.", field="purchased_at"
            )
        product_ids = [item.product_id for item in command.items]
        prices = await self._prices.list_prices(command.store_id, product_ids)
        cycle = await self._cycles.cycle_of(command.account_id, command.purchased_at)
        purchase = Purchase.register(
            store_id=command.store_id,
            account_id=command.account_id,
            cycle_id=cycle.cycle_id,
            cycle_payment_date=cycle.payment_date,
            purchased_at=command.purchased_at,
            purchase_day=command.purchased_at.astimezone(now.tzinfo).date(),
            mode=command.mode,
            items=[
                PurchaseItem(item.product_id, item.quantity, prices[item.product_id])
                for item in command.items
            ],
            tea=terms.tea,
            late_tea=terms.late_tea,
            installments_count=command.installments_count,
            max_weeks=terms.max_weeks,
            created_by=command.created_by,
        )
        active = await self._purchases.list_active_by_account(command.account_id)
        available = terms.credit_limit.amount - outstanding_principal_of(active).amount
        if purchase.amount.amount > available:
            readable_available = f"{max(available, Decimal(0)):.2f}"
            raise BusinessError(
                "CREDIT_LIMIT_EXCEEDED",
                f"The purchase exceeds the available credit (S/ {readable_available}).",
                details={"available": readable_available},
            )
        return purchase

    async def register(self, command: RegisterPurchaseCommand, now: datetime) -> Purchase:
        """Save the purchase and its cycle together, once every check passed."""
        purchase = await self.simulate(command, now)
        await self._purchases.add(purchase)
        await self._unit_of_work.commit()
        return purchase
