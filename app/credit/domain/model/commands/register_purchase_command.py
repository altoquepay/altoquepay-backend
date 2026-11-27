from dataclasses import dataclass
from datetime import datetime

from app.credit.domain.model.aggregates.purchase import PaymentMode


@dataclass(frozen=True)
class RequestedItem:
    product_id: int
    quantity: int


@dataclass(frozen=True)
class RegisterPurchaseCommand:
    """The store sells; the server sets the prices and rates."""

    store_id: int
    account_id: int
    purchased_at: datetime
    mode: PaymentMode
    installments_count: int | None
    items: list[RequestedItem]
    created_by: int
    # Weeks of total grace the store gives a weekly purchase before its installments.
    grace_weeks: int = 0
