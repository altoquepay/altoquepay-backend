from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.billing.application.command_services.cycle_closing_service import CycleClosingService
from app.billing.application.ports.account_directory import AccountDirectory
from app.billing.application.ports.credit_ledger import (
    WEEKLY,
    CreditLedger,
    InstallmentInfo,
    PurchaseInfo,
)
from app.billing.domain.model.aggregates.billing_cycle import CycleStatus
from app.billing.domain.model.aggregates.payment import (
    Payment,
    PaymentBreakdown,
    PaymentKind,
)
from app.billing.domain.repositories.billing_cycle_repository import BillingCycleRepository
from app.billing.domain.repositories.payment_repository import PaymentRepository
from app.billing.domain.services.payment_calculations import (
    ZERO,
    interest_for_days,
    late_interest,
    savings,
)
from app.shared.domain.errors import BusinessError
from app.shared.domain.finance import INSTALLMENT_PERIOD_DAYS
from app.shared.domain.value_objects import Money
from app.shared.infrastructure.unit_of_work import UnitOfWork

# The field each kind of payment names its target with.
TARGET_FIELDS = {
    PaymentKind.CYCLE_STATEMENT: "cycle_id",
    PaymentKind.INSTALLMENT: "installment_id",
    PaymentKind.INSTALLMENT_ADVANCE: "installment_id",
    PaymentKind.SINGLE_DATE_EARLY: "purchase_id",
    PaymentKind.FULL_PREPAYMENT: "purchase_id",
}


@dataclass(frozen=True)
class PaymentTarget:
    """What to pay: the kind and the one id it needs, cycle, installment or purchase."""

    kind: PaymentKind
    cycle_id: int | None = None
    installment_id: int | None = None
    purchase_id: int | None = None

    def target_id(self) -> int:
        """Return the id the kind needs. Raise INVALID_PAYMENT_TARGET if it is missing or extra."""
        needed = TARGET_FIELDS[self.kind]
        for field in ("cycle_id", "installment_id", "purchase_id"):
            given = getattr(self, field) is not None
            if field == needed and not given:
                raise BusinessError(
                    "INVALID_PAYMENT_TARGET",
                    f"A {self.kind} payment needs {needed}.",
                    field=needed,
                )
            if field != needed and given:
                raise BusinessError(
                    "INVALID_PAYMENT_TARGET",
                    f"A {self.kind} payment takes {needed}, not {field}.",
                    field=field,
                )
        return getattr(self, needed)


@dataclass(frozen=True)
class PaymentQuote:
    """days_late counts from the due date; interest_days are the days early payments charge."""

    target: PaymentTarget
    account_id: int
    paid_on: date
    breakdown: PaymentBreakdown
    days_late: int = 0
    interest_days: int | None = None


def already_paid() -> BusinessError:
    return BusinessError("ALREADY_PAID", "It was already paid.", status=409)


def not_found(target: str) -> BusinessError:
    return BusinessError("NOT_FOUND", f"The {target} does not exist.", status=404)


class PaymentService:
    """Quotes and registers payments. There are no partial payments: each covers its target."""

    def __init__(
        self,
        cycles: BillingCycleRepository,
        payments: PaymentRepository,
        ledger: CreditLedger,
        accounts: AccountDirectory,
        unit_of_work: UnitOfWork,
        business_time_zone: ZoneInfo,
    ) -> None:
        self._cycles = cycles
        self._payments = payments
        self._ledger = ledger
        self._accounts = accounts
        self._unit_of_work = unit_of_work
        self._business_time_zone = business_time_zone
        self._closing = CycleClosingService(cycles, ledger)

    async def quote(
        self, store_id: int, target: PaymentTarget, today: date, now: datetime
    ) -> PaymentQuote:
        """Calculate what paying today would take, without saving anything."""
        account_id = await self._account_of_store(store_id, target)
        return await self._quote(account_id, target, today, now)

    async def register(
        self,
        store_id: int,
        target: PaymentTarget,
        amount: Money,
        user_id: int,
        today: date,
        now: datetime,
    ) -> Payment:
        """Register a payment of exactly the amount due and mark what it paid in credit."""
        account_id = await self._account_of_store(store_id, target)
        # Locked first, so two payments of the same account cannot both pass the checks.
        await self._accounts.lock(account_id)
        quote = await self._quote(account_id, target, today, now)
        payment = Payment(
            store_id=store_id,
            account_id=account_id,
            kind=target.kind,
            paid_on=today,
            breakdown=quote.breakdown.apply(amount),
            created_by=user_id,
            cycle_id=target.cycle_id,
            installment_id=target.installment_id,
            purchase_id=target.purchase_id,
        )
        await self._payments.add(payment)
        if payment.id is None:
            raise ValueError("The payment was not stored.")
        await self._settle(quote, payment.id)
        await self._unit_of_work.commit()
        return payment

    async def _account_of_store(self, store_id: int, target: PaymentTarget) -> int:
        """Return the account the target belongs to; targets of other stores are not found."""
        target_id = target.target_id()
        if target.kind == PaymentKind.CYCLE_STATEMENT:
            name = "cycle"
            cycle = await self._cycles.find_by_id(target_id)
            if cycle is None:
                raise not_found(name)
            account_id = cycle.store_customer_id
        elif target.installment_id is not None:
            name = "installment"
            account_id = (await self._ledger.get_installment(target_id)).account_id
        else:
            name = "purchase"
            account_id = (await self._ledger.get_purchase(target_id)).account_id
        if (await self._accounts.get_account(account_id)).store_id != store_id:
            raise not_found(name)
        return account_id

    async def _quote(
        self, account_id: int, target: PaymentTarget, today: date, now: datetime
    ) -> PaymentQuote:
        # A cycle whose cutoff ended must be closed before deciding what can be paid.
        await self._closing.close_due(today, now, account_id=account_id)
        match target.kind:
            case PaymentKind.CYCLE_STATEMENT:
                return await self._quote_cycle(account_id, target, today)
            case PaymentKind.INSTALLMENT | PaymentKind.INSTALLMENT_ADVANCE:
                return await self._quote_installment(account_id, target, today)
            case PaymentKind.SINGLE_DATE_EARLY:
                return await self._quote_single_date_early(account_id, target, today)
            case PaymentKind.FULL_PREPAYMENT:
                return await self._quote_full_prepayment(account_id, target, today)

    async def _quote_cycle(
        self, account_id: int, target: PaymentTarget, today: date
    ) -> PaymentQuote:
        cycle = await self._cycles.find_by_id(target.target_id())
        if cycle is None or cycle.id is None:
            raise not_found("cycle")
        if cycle.status == CycleStatus.PAID:
            raise already_paid()
        if cycle.is_open:
            raise BusinessError(
                "CYCLE_NOT_CLOSED",
                "The cycle is still open. Pay its purchases early with SINGLE_DATE_EARLY.",
                status=409,
            )
        days_late = max((today - cycle.payment_date).days, 0)
        billed = [
            p for p in await self._ledger.cycle_purchases(cycle.id) if p.is_active_single_date
        ]
        totals = cycle.statement_totals()
        breakdown = PaymentBreakdown(
            late_interest=late_interest_of(billed, days_late),
            ordinary_interest=totals.ordinary_interest,
            principal=totals.capital,
        )
        return PaymentQuote(target, account_id, today, breakdown, days_late)

    async def _quote_installment(
        self, account_id: int, target: PaymentTarget, today: date
    ) -> PaymentQuote:
        installment = await self._ledger.get_installment(target.target_id())
        if not installment.is_pending:
            raise already_paid()
        pending = await self._pending_of(account_id, installment.purchase_id)
        if pending[0].installment_id != installment.installment_id:
            raise BusinessError(
                "INSTALLMENT_OUT_OF_ORDER",
                f"Installment {pending[0].number} of this purchase must be paid first.",
                status=409,
                details={"next_installment_id": str(pending[0].installment_id)},
            )
        is_due = today >= installment.due_date
        if target.kind == PaymentKind.INSTALLMENT_ADVANCE and is_due:
            raise kind_mismatch("The installment is already due; pay it as INSTALLMENT.")
        if target.kind == PaymentKind.INSTALLMENT and not is_due:
            raise kind_mismatch("The installment is not due yet; pay it as INSTALLMENT_ADVANCE.")
        purchase = await self._ledger.get_purchase(installment.purchase_id)
        days_late = max((today - installment.due_date).days, 0)
        breakdown = PaymentBreakdown(
            late_interest=late_interest(installment.amount, purchase.late_tea, days_late),
            ordinary_interest=installment.interest,
            principal=installment.amortization,
        )
        return PaymentQuote(target, account_id, today, breakdown, days_late)

    async def _quote_single_date_early(
        self, account_id: int, target: PaymentTarget, today: date
    ) -> PaymentQuote:
        purchase = await self._active_purchase(target, "SINGLE_DATE")
        cycle = await self._cycles.find_by_id(purchase.cycle_id)
        if cycle is None or not cycle.is_open:
            raise BusinessError(
                "PURCHASE_IN_STATEMENT",
                "The purchase is already billed in a closed cycle; pay the cycle statement.",
                status=409,
            )
        days = (today - self._purchase_day(purchase)).days
        ordinary = interest_for_days(purchase.amount, purchase.tea, days)
        breakdown = PaymentBreakdown(
            late_interest=ZERO,
            ordinary_interest=ordinary,
            principal=purchase.amount,
            savings=savings(purchase.ordinary_interest, ordinary),
        )
        return PaymentQuote(target, account_id, today, breakdown, interest_days=days)

    async def _quote_full_prepayment(
        self, account_id: int, target: PaymentTarget, today: date
    ) -> PaymentQuote:
        purchase = await self._active_purchase(target, WEEKLY)
        pending = await self._pending_of(account_id, purchase.purchase_id)
        if any(installment.due_date < today for installment in pending):
            raise BusinessError(
                "PREPAYMENT_WITH_OVERDUE",
                "The purchase has overdue installments; pay them before prepaying the rest.",
                status=409,
            )
        first = pending[0]
        # The installments run every 7 days from the cycle payment date.
        last_due_paid = first.due_date - timedelta(days=INSTALLMENT_PERIOD_DAYS)
        if first.number == 1 and today < last_due_paid:
            # Still in the grace period: only the days since the purchase are charged.
            principal = purchase.amount
            days = (today - self._purchase_day(purchase)).days
        else:
            # The balance after the last installment paid, plus its interest since then.
            principal = first.opening_balance
            days = max((today - last_due_paid).days, 0)
        ordinary = interest_for_days(principal, purchase.tea, days)
        owed = Money(sum((i.amount.amount for i in pending), Decimal(0)))
        breakdown = PaymentBreakdown(
            late_interest=ZERO,
            ordinary_interest=ordinary,
            principal=principal,
            savings=savings(Money(owed.amount - principal.amount), ordinary),
        )
        return PaymentQuote(target, account_id, today, breakdown, interest_days=days)

    async def _settle(self, quote: PaymentQuote, payment_id: int) -> None:
        """Mark in credit, and in the cycle, what the payment paid."""
        target = quote.target
        match target.kind:
            case PaymentKind.CYCLE_STATEMENT:
                cycle = await self._cycles.find_by_id(target.target_id())
                if cycle is None or cycle.id is None:
                    raise not_found("cycle")
                for purchase in await self._ledger.cycle_purchases(cycle.id):
                    if purchase.is_active_single_date:
                        await self._ledger.mark_purchase_paid(purchase.purchase_id, payment_id)
                cycle.mark_paid(quote.breakdown.late_interest)
                await self._cycles.update(cycle)
            case PaymentKind.INSTALLMENT | PaymentKind.INSTALLMENT_ADVANCE:
                await self._ledger.mark_installment_paid(target.target_id(), payment_id)
            case PaymentKind.SINGLE_DATE_EARLY:
                await self._ledger.mark_purchase_paid(target.target_id(), payment_id)
            case PaymentKind.FULL_PREPAYMENT:
                await self._ledger.cancel_remaining_installments(target.target_id(), payment_id)

    async def _active_purchase(self, target: PaymentTarget, mode: str) -> PurchaseInfo:
        purchase = await self._ledger.get_purchase(target.target_id())
        if purchase.mode != mode:
            raise BusinessError(
                "INVALID_PAYMENT_TARGET",
                f"A {target.kind} payment is for {mode} purchases.",
                field="purchase_id",
            )
        if purchase.status != "ACTIVE":
            raise already_paid()
        return purchase

    async def _pending_of(self, account_id: int, purchase_id: int) -> list[InstallmentInfo]:
        pending = [
            installment
            for installment in await self._ledger.pending_installments(account_id)
            if installment.purchase_id == purchase_id
        ]
        if not pending:
            raise already_paid()
        return sorted(pending, key=lambda installment: installment.number)

    def _purchase_day(self, purchase: PurchaseInfo) -> date:
        return purchase.purchased_at.astimezone(self._business_time_zone).date()


def late_interest_of(purchases: list[PurchaseInfo], days_late: int) -> Money:
    """Late interest of a statement: each purchase's total at its own late rate, then summed."""
    return Money(
        sum(
            (late_interest(p.total, p.late_tea, days_late).amount for p in purchases),
            Decimal(0),
        )
    )


def kind_mismatch(message: str) -> BusinessError:
    return BusinessError("PAYMENT_KIND_MISMATCH", message, field="kind")
