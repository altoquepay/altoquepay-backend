from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from app.shared.domain.value_objects import Money, Rate

SINGLE_DATE = "SINGLE_DATE"
WEEKLY = "WEEKLY"
ACTIVE = "ACTIVE"
PENDING_STATUSES = {"PENDING", "OVERDUE"}


@dataclass(frozen=True)
class PurchaseInfo:
    purchase_id: int
    account_id: int
    cycle_id: int
    purchased_at: datetime
    mode: str
    amount: Money
    tea: Rate
    late_tea: Rate
    ordinary_interest: Money
    status: str

    @property
    def is_active_single_date(self) -> bool:
        return self.mode == SINGLE_DATE and self.status == ACTIVE

    @property
    def total(self) -> Money:
        """What a single date purchase owes on its payment date."""
        return Money(self.amount.amount + self.ordinary_interest.amount)


@dataclass(frozen=True)
class InstallmentInfo:
    installment_id: int
    purchase_id: int
    account_id: int
    number: int
    due_date: date
    opening_balance: Money
    interest: Money
    amortization: Money
    amount: Money
    status: str

    @property
    def is_pending(self) -> bool:
        return self.status in PENDING_STATUSES


class CreditLedger(ABC):
    """The purchases and installments billing charges, answered by the credit context.

    Every method raises NOT_FOUND (404) for a missing id, and the marks raise ALREADY_PAID (409).
    None of them commits.
    """

    @abstractmethod
    async def get_purchase(self, purchase_id: int) -> PurchaseInfo: ...

    @abstractmethod
    async def get_installment(self, installment_id: int) -> InstallmentInfo: ...

    @abstractmethod
    async def pending_installments(self, account_id: int) -> list[InstallmentInfo]:
        """Return the pending and overdue installments of an account, by due date."""

    @abstractmethod
    async def cycle_purchases(self, cycle_id: int) -> list[PurchaseInfo]: ...

    @abstractmethod
    async def mark_installment_paid(self, installment_id: int, payment_id: int) -> None: ...

    @abstractmethod
    async def mark_purchase_paid(self, purchase_id: int, payment_id: int) -> None: ...

    @abstractmethod
    async def cancel_remaining_installments(self, purchase_id: int, payment_id: int) -> None: ...
