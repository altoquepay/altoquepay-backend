"""An account: the credit conditions one store gives one customer."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.shared.domain.value_objects import CreditConditions, Money

# AlToque Pay only lends in soles.
CURRENCY = "PEN"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass
class StoreCustomer:
    """An inactive account keeps its history, but the customer can no longer buy on credit."""

    store_id: int
    customer_id: int
    credit_limit: Money
    conditions: CreditConditions
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: datetime | None = None
    id: int | None = None

    @property
    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE
