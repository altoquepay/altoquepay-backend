"""The only way other bounded contexts may reach the credit context.

Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.shared.infrastructure.unit_of_work import UnitOfWork


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
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def get_outstanding_principal(self, account_id: int) -> Decimal:
        """Return the unpaid single-date purchases plus the principal of unpaid installments."""
        raise NotImplementedError

    async def get_installments_due(
        self, account_id: int, from_date: date, to_date: date
    ) -> list[InstallmentSummary]:
        """Return the pending and overdue installments due within the inclusive date range."""
        raise NotImplementedError

    async def get_installment(self, installment_id: int) -> InstallmentSummary:
        """Return an installment, since a payment quote receives only its id."""
        raise NotImplementedError

    async def get_purchase(self, purchase_id: int) -> PurchaseSummary:
        """Return a purchase, since a payment quote receives only its id."""
        raise NotImplementedError

    async def get_cycle_purchases(self, cycle_id: int) -> list[PurchaseSummary]:
        """Return the purchases of a cycle in both modes. Callers filter by mode."""
        raise NotImplementedError

    async def mark_installment_paid(self, installment_id: int, payment_id: int) -> None:
        """Mark an installment as paid, and its purchase too if it was the last one.

        Raises ALREADY_PAID (409) if it was already paid.
        """
        raise NotImplementedError

    async def mark_purchase_paid(self, purchase_id: int, payment_id: int) -> None:
        """Mark a purchase as PAID, even when paid early. Raises ALREADY_PAID (409) if it was."""
        raise NotImplementedError

    async def cancel_remaining_installments(self, purchase_id: int, payment_id: int) -> None:
        """Mark the unpaid installments as CANCELLED and the purchase as PREPAID.

        Billing must reject the prepayment first if any installment is overdue.
        """
        raise NotImplementedError

    async def list_purchases(self, account_id: int) -> list[PurchaseSummary]:
        """Return the purchases of an account, most recent first."""
        raise NotImplementedError
