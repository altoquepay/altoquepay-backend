"""The only way other bounded contexts may reach the credit context.

Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.credit.domain.model.aggregates.purchase import Purchase, outstanding_principal_of
from app.credit.domain.repositories.purchase_repository import InstallmentEntry
from app.credit.infrastructure.persistence.purchase_repository_impl import PurchaseRepositoryImpl
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.shared.interfaces.rest.business_date import get_business_today


@dataclass(frozen=True)
class PurchaseSummary:
    purchase_id: int
    account_id: int
    cycle_id: int
    purchased_at: datetime
    mode: str
    amount: Decimal
    tea: Decimal
    late_tea: Decimal
    term_days: int | None
    installments_count: int | None
    installment_amount: Decimal | None
    ordinary_interest: Decimal
    status: str


@dataclass(frozen=True)
class InstallmentSummary:
    installment_id: int
    purchase_id: int
    account_id: int
    number: int
    due_date: date
    opening_balance: Decimal
    interest: Decimal
    amortization: Decimal
    amount: Decimal
    status: str


class CreditFacade:
    """Never commits: the use case of the calling context does, once all its work succeeded."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._purchases = PurchaseRepositoryImpl(unit_of_work.session)

    async def get_outstanding_principal(self, account_id: int) -> Decimal:
        """Return the unpaid single-date purchases plus the principal of unpaid installments."""
        active = await self._purchases.list_active_by_account(account_id)
        return outstanding_principal_of(active).amount

    async def get_installments_due(
        self, account_id: int, from_date: date, to_date: date
    ) -> list[InstallmentSummary]:
        """Return the pending and overdue installments due within the inclusive date range."""
        entries = await self._purchases.list_installments_due(account_id, from_date, to_date)
        return [to_installment_summary(entry) for entry in entries]

    async def get_installment(self, installment_id: int) -> InstallmentSummary:
        """Return an installment, since a payment quote receives only its id."""
        entry = await self._purchases.find_installment(installment_id)
        if entry is None:
            raise BusinessError("NOT_FOUND", "The installment does not exist.", status=404)
        return to_installment_summary(entry)

    async def get_purchase(self, purchase_id: int) -> PurchaseSummary:
        """Return a purchase, since a payment quote receives only its id."""
        return to_purchase_summary(await self._find(purchase_id))

    async def get_cycle_purchases(self, cycle_id: int) -> list[PurchaseSummary]:
        """Return the purchases of a cycle in both modes. Callers filter by mode."""
        return [to_purchase_summary(p) for p in await self._purchases.list_by_cycle(cycle_id)]

    async def mark_installment_paid(self, installment_id: int, payment_id: int) -> None:
        """Mark an installment as paid, and its purchase too if it was the last one.

        Raises ALREADY_PAID (409) if it was already paid.
        """
        purchase = await self._purchases.find_by_installment(installment_id)
        if purchase is None:
            raise BusinessError("NOT_FOUND", "The installment does not exist.", status=404)
        purchase.mark_installment_paid(installment_id, payment_id)
        await self._purchases.update(purchase)

    async def mark_purchase_paid(self, purchase_id: int, payment_id: int) -> None:
        """Mark a purchase as PAID, even when paid early. Raises ALREADY_PAID (409) if it was."""
        purchase = await self._find(purchase_id)
        purchase.mark_paid(payment_id)
        await self._purchases.update(purchase)

    async def cancel_remaining_installments(self, purchase_id: int, payment_id: int) -> None:
        """Mark the unpaid installments as CANCELLED and the purchase as PREPAID.

        Billing must reject the prepayment first if any installment is overdue.
        """
        purchase = await self._find(purchase_id)
        purchase.cancel_remaining_installments(payment_id)
        await self._purchases.update(purchase)

    async def list_purchases(self, account_id: int) -> list[PurchaseSummary]:
        """Return the purchases of an account, most recent first."""
        return [to_purchase_summary(p) for p in await self._purchases.list_by_account(account_id)]

    async def _find(self, purchase_id: int) -> Purchase:
        purchase = await self._purchases.find_by_id(purchase_id)
        if purchase is None:
            raise BusinessError("NOT_FOUND", "The purchase does not exist.", status=404)
        return purchase


def to_purchase_summary(purchase: Purchase) -> PurchaseSummary:
    if purchase.id is None:
        raise ValueError("Only a stored purchase has a summary.")
    return PurchaseSummary(
        purchase_id=purchase.id,
        account_id=purchase.account_id,
        cycle_id=purchase.cycle_id,
        purchased_at=purchase.purchased_at,
        mode=purchase.mode.value,
        amount=purchase.amount.amount,
        tea=purchase.tea.percent,
        late_tea=purchase.late_tea.percent,
        term_days=purchase.term_days,
        installments_count=purchase.installments_count,
        installment_amount=(
            None if purchase.installment_amount is None else purchase.installment_amount.amount
        ),
        ordinary_interest=purchase.ordinary_interest.amount,
        status=purchase.status.value,
    )


def to_installment_summary(entry: InstallmentEntry) -> InstallmentSummary:
    installment = entry.installment
    if installment.id is None:
        raise ValueError("Only a stored installment has a summary.")
    return InstallmentSummary(
        installment_id=installment.id,
        purchase_id=entry.purchase_id,
        account_id=entry.account_id,
        number=installment.number,
        due_date=installment.due_date,
        opening_balance=installment.opening_balance.amount,
        interest=installment.interest.amount,
        amortization=installment.amortization.amount,
        amount=installment.amount.amount,
        # A pending installment past its due date is reported as OVERDUE.
        status=installment.status_on(get_business_today()).value,
    )
