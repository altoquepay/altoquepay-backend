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
    # Weekly only: the weeks of the plan the store makes of total grace, counted from the
    # purchase: at the start, between installments or none, never the last one.
    grace_weeks: tuple[int, ...] = ()
