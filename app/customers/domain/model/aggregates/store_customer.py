"""An account: the credit conditions one store gives one customer."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.shared.domain.value_objects import CreditConditions, Money

# AlToque Pay only lends in soles.
CURRENCY = "PEN"
# How long the customer has to redeem the access code a store handed them.
ACCESS_CODE_LIFETIME = timedelta(hours=48)


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass
class StoreCustomer:
    """An inactive account keeps its history, but the customer can no longer buy on credit.

    The customer sees the account in their portal only once it is linked, which takes the
    access code this store hands them, so no other store can link it or see it.
    """

    store_id: int
    customer_id: int
    credit_limit: Money
    conditions: CreditConditions
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: datetime | None = None
    portal_linked_at: datetime | None = None
    access_code_hash: str | None = None
    access_code_expires_at: datetime | None = None
    id: int | None = None

    @property
    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE

    @property
    def is_portal_linked(self) -> bool:
        return self.portal_linked_at is not None

    def update_terms(self, credit_limit: Money, conditions: CreditConditions) -> None:
        """New terms apply to new purchases; registered ones keep the rates they were made with."""
        self.credit_limit = credit_limit
        self.conditions = conditions

    def deactivate(self) -> None:
        self.status = AccountStatus.INACTIVE

    def issue_access_code(self, code_hash: str, now: datetime) -> datetime:
        """Keep the hash of a new code, which replaces the previous one. Return when it expires."""
        self.access_code_hash = code_hash
        self.access_code_expires_at = now + ACCESS_CODE_LIFETIME
        return self.access_code_expires_at

    def accepts(self, code_hash: str, now: datetime) -> bool:
        return (
            self.access_code_hash == code_hash
            and self.access_code_expires_at is not None
            and now < self.access_code_expires_at
        )

    def link_portal(self, now: datetime) -> None:
        """Show the account in the customer's portal. The code that allowed it is spent."""
        self.portal_linked_at = now
        self.access_code_hash = None
        self.access_code_expires_at = None

    def unlink_portal(self) -> None:
        """Hide the account from the portal until the customer redeems a new code of this store."""
        self.portal_linked_at = None
