"""An account: the credit conditions one store gives one customer."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import CreditConditions, Money

# AlToque Pay only lends in soles.
CURRENCY = "PEN"
NAMES_MAXIMUM_LENGTH = 100
# How long the customer has to redeem the access code a store handed them.
ACCESS_CODE_LIFETIME = timedelta(hours=48)


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass
class StoreCustomer:
    """An inactive account keeps its history, but the customer can no longer buy on credit.

    The names and contact data are how this store knows the person; other stores keep their own.
    The customer sees the account in their portal only once it is linked, which takes the
    access code this store hands them, so no other store can link it or see it. A linked
    account stays trusted after it leaves the portal: only a trusted store may restore the
    customer's access, so a store cannot open an account for someone's DNI and take it over.
    """

    store_id: int
    customer_id: int
    first_names: str
    last_names: str
    credit_limit: Money
    conditions: CreditConditions
    phone: str | None = None
    address: str | None = None
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: datetime | None = None
    portal_linked_at: datetime | None = None
    portal_trusted: bool = False
    access_code_hash: str | None = None
    access_code_expires_at: datetime | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.first_names = required_name(self.first_names, "first_names")
        self.last_names = required_name(self.last_names, "last_names")
        self.phone = blank_as_none(self.phone)
        self.address = blank_as_none(self.address)

    @property
    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE

    @property
    def is_portal_linked(self) -> bool:
        return self.portal_linked_at is not None

    def update_contact(
        self, first_names: str, last_names: str, phone: str | None, address: str | None
    ) -> None:
        """Change the person's data in this store only. The DNI is their identity, so it stays."""
        self.first_names = first_names
        self.last_names = last_names
        self.phone = phone
        self.address = address
        self.__post_init__()

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
        """Show the account in the customer's portal and trust its store. The code is spent."""
        self.portal_linked_at = now
        self.portal_trusted = True
        self.access_code_hash = None
        self.access_code_expires_at = None

    def unlink_portal(self) -> None:
        """Hide the account from the portal until the customer redeems a new code of this store."""
        self.portal_linked_at = None

    def trust_portal(self) -> None:
        """Let this store restore the customer's access, as support decided."""
        self.portal_trusted = True

    def distrust_portal(self) -> None:
        """Take the account out of the portal and stop its store from restoring the access."""
        self.portal_trusted = False
        self.unlink_portal()


def required_name(name: str | None, field: str) -> str:
    name = (name or "").strip()
    if not 1 <= len(name) <= NAMES_MAXIMUM_LENGTH:
        raise BusinessError(
            "INVALID_NAME",
            f"The name must have between 1 and {NAMES_MAXIMUM_LENGTH} characters.",
            field=field,
        )
    return name


def blank_as_none(text: str | None) -> str | None:
    return (text or "").strip() or None
