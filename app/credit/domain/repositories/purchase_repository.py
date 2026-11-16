from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from app.credit.domain.model.aggregates.purchase import (
    Installment,
    InstallmentStatus,
    PaymentMode,
    Purchase,
)


@dataclass(frozen=True)
class PurchaseFilter:
    """N11 filters. Every field is optional; the dates are days in the business time zone."""

    account_id: int | None = None
    mode: PaymentMode | None = None
    from_date: date | None = None
    to_date: date | None = None


@dataclass(frozen=True)
class InstallmentEntry:
    """An installment with the purchase and account it belongs to, for lists across purchases."""

    installment: Installment
    purchase_id: int
    account_id: int


class PurchaseRepository(ABC):
    @abstractmethod
    async def find_by_id(self, purchase_id: int) -> Purchase | None:
        """Return the purchase with its items and installments."""

    @abstractmethod
    async def find_by_installment(self, installment_id: int) -> Purchase | None: ...

    @abstractmethod
    async def add(self, purchase: Purchase) -> None:
        """Store a new purchase and set its id and the ids of its installments."""

    @abstractmethod
    async def update(self, purchase: Purchase) -> None:
        """Save the status and payment of the purchase and of its installments."""

    @abstractmethod
    async def list_active_by_account(self, account_id: int) -> list[Purchase]: ...

    @abstractmethod
    async def list_by_account(self, account_id: int) -> list[Purchase]:
        """Return every purchase of the account, most recent first."""

    @abstractmethod
    async def list_by_cycle(self, cycle_id: int) -> list[Purchase]: ...

    @abstractmethod
    async def list_page(
        self, store_id: int, purchase_filter: PurchaseFilter, offset: int, size: int
    ) -> tuple[list[Purchase], int]:
        """Return a page of the store's purchases, most recent first, and the total count."""

    @abstractmethod
    async def list_installments(
        self,
        store_id: int,
        status: InstallmentStatus | None,
        due_before: date | None,
        today: date,
        offset: int,
        size: int,
    ) -> tuple[list[InstallmentEntry], int]:
        """Return a page of the store's installments by due date, and the total count.

        OVERDUE selects the pending ones due before today, and PENDING the rest of them.
        """

    @abstractmethod
    async def list_installments_due(
        self, account_id: int, from_date: date, to_date: date
    ) -> list[InstallmentEntry]:
        """Return the pending installments due within the inclusive range, by due date."""

    @abstractmethod
    async def find_installment(self, installment_id: int) -> InstallmentEntry | None: ...
