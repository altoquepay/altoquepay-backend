from datetime import date, datetime
from decimal import Decimal

from app.billing.application.ports.credit_ledger import CreditLedger, PurchaseInfo
from app.billing.domain.model.aggregates.billing_cycle import BillingCycle, StatementTotals
from app.billing.domain.repositories.billing_cycle_repository import BillingCycleRepository
from app.shared.domain.value_objects import Money


def totals_of(purchases: list[PurchaseInfo]) -> StatementTotals:
    """What the unpaid single date purchases owe on the payment date."""
    billed = [purchase for purchase in purchases if purchase.is_active_single_date]
    return StatementTotals(
        capital=Money(sum((p.amount.amount for p in billed), Decimal(0))),
        ordinary_interest=Money(sum((p.ordinary_interest.amount for p in billed), Decimal(0))),
    )


class CycleClosingService:
    """Closes cycles whose cutoff day ended, fixing their statement.

    There is no scheduler, so billing closes them when it first touches them after the cutoff.
    It never commits: the use case that calls it does, or the closing is redone next time.
    """

    def __init__(self, cycles: BillingCycleRepository, ledger: CreditLedger) -> None:
        self._cycles = cycles
        self._ledger = ledger

    async def close_due(
        self,
        today: date,
        now: datetime,
        *,
        store_id: int | None = None,
        account_id: int | None = None,
    ) -> None:
        due = await self._cycles.list_due_for_closing(
            today, store_id=store_id, account_id=account_id
        )
        for cycle in due:
            await self.close(cycle, now)

    async def close(self, cycle: BillingCycle, now: datetime) -> None:
        if cycle.id is None:
            raise ValueError("Only a stored cycle can be closed.")
        cycle.close(totals_of(await self._ledger.cycle_purchases(cycle.id)), now)
        await self._cycles.update(cycle)
