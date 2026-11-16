from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from app.billing.domain.model.aggregates.payment import Payment, PaymentKind


@dataclass(frozen=True)
class PaymentFilter:
    """from_date and to_date are inclusive days of payment."""

    account_id: int | None = None
    kind: PaymentKind | None = None
    from_date: date | None = None
    to_date: date | None = None


class PaymentRepository(ABC):
    @abstractmethod
    async def list_by_account(self, account_id: int) -> list[Payment]:
        """Return the payments of an account, most recent first."""

    @abstractmethod
    async def list_page(
        self, store_id: int, payment_filter: PaymentFilter, offset: int, size: int
    ) -> tuple[list[Payment], int]:
        """Return a page of the store's payments, most recent first, and the total."""

    @abstractmethod
    async def add(self, payment: Payment) -> None:
        """Store a new payment and set its id and creation time."""
