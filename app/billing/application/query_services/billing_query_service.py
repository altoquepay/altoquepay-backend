from dataclasses import dataclass
from datetime import date, datetime

from app.billing.application.command_services.cycle_closing_service import (
    CycleClosingService,
    totals_of,
)
from app.billing.application.command_services.payment_service import late_interest_of
from app.billing.application.ports.account_directory import AccountDirectory
from app.billing.application.ports.credit_ledger import CreditLedger, PurchaseInfo
from app.billing.domain.model.aggregates.billing_cycle import (
    BillingCycle,
    CycleStatus,
    StatementTotals,
)
from app.billing.domain.model.aggregates.payment import Payment
from app.billing.domain.repositories.billing_cycle_repository import (
    BillingCycleRepository,
    CycleFilter,
)
from app.billing.domain.repositories.payment_repository import PaymentFilter, PaymentRepository
from app.billing.domain.services.payment_calculations import ZERO
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money


@dataclass(frozen=True)
class Statement:
    """A cycle's statement on a day. An open cycle adds up its purchases as they are now;
    an overdue one adds the late interest up to that day.
    """

    cycle: BillingCycle
    status: CycleStatus
    totals: StatementTotals
    late_interest: Money
    purchases: list[PurchaseInfo]

    @property
    def total(self) -> Money:
        return Money(self.totals.total.amount + self.late_interest.amount)


class BillingQueryService:
    """Closes the cycles whose cutoff ended before reading them. It never commits."""

    def __init__(
        self,
        cycles: BillingCycleRepository,
        payments: PaymentRepository,
        ledger: CreditLedger,
    ) -> None:
        self._cycles = cycles
        self._payments = payments
        self._ledger = ledger
        self._closing = CycleClosingService(cycles, ledger)

    async def get_statement(
        self, account_id: int, year: int, month: int, today: date, now: datetime
    ) -> Statement | None:
        """Return the statement of a month, or None if the account has no cycle in it."""
        await self._closing.close_due(today, now, account_id=account_id)
        cycle = await self._cycles.find(account_id, year, month)
        if cycle is None or cycle.id is None:
            return None
        purchases = await self._ledger.cycle_purchases(cycle.id)
        status = cycle.status_on(today)
        if cycle.is_open:
            totals, late = totals_of(purchases), ZERO
        elif status == CycleStatus.PAID:
            totals, late = cycle.statement_totals(), cycle.late_interest or ZERO
        else:
            days_late = max((today - cycle.payment_date).days, 0)
            billed = [p for p in purchases if p.is_active_single_date]
            totals, late = cycle.statement_totals(), late_interest_of(billed, days_late)
        return Statement(cycle, status, totals, late, purchases)

    async def get_store_statement(
        self,
        accounts: AccountDirectory,
        store_id: int,
        account_id: int,
        year: int,
        month: int,
        today: date,
        now: datetime,
    ) -> Statement:
        """Raise NOT_FOUND (404) for an account of another store or a month without a cycle."""
        if (await accounts.get_account(account_id)).store_id != store_id:
            raise BusinessError("NOT_FOUND", "The customer account does not exist.", status=404)
        statement = await self.get_statement(account_id, year, month, today, now)
        if statement is None:
            raise BusinessError("NOT_FOUND", "The account has no cycle in that month.", status=404)
        return statement

    async def list_cycles(
        self,
        store_id: int,
        cycle_filter: CycleFilter,
        today: date,
        now: datetime,
        offset: int,
        size: int,
    ) -> tuple[list[BillingCycle], int]:
        await self._closing.close_due(today, now, store_id=store_id)
        return await self._cycles.list_page(store_id, cycle_filter, today, offset, size)

    async def list_payments(self, account_id: int) -> list[Payment]:
        return await self._payments.list_by_account(account_id)

    async def list_store_payments(
        self, store_id: int, payment_filter: PaymentFilter, offset: int, size: int
    ) -> tuple[list[Payment], int]:
        return await self._payments.list_page(store_id, payment_filter, offset, size)
