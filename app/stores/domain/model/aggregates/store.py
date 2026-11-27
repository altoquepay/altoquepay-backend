"""A bodega that sells on credit to its customers through AlToque Pay."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import CreditConditions, Rate, Ruc

BUSINESS_NAME_MAXIMUM_LENGTH = 150

# Taken from the report's design and algorithm; each store changes them in its profile.
INITIAL_CONDITIONS = CreditConditions(
    cutoff_day=10,
    payment_day=15,
    tea=Rate.from_percent(Decimal("40")),
    late_tea=Rate.from_percent(Decimal("60")),
    max_weeks=4,
)


class StoreStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass
class Store:
    """An inactive store keeps its data, but its administrator can no longer work in it."""

    business_name: str
    ruc: Ruc
    default_conditions: CreditConditions
    address: str | None = None
    phone: str | None = None
    status: StoreStatus = StoreStatus.ACTIVE
    registered_at: datetime | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.business_name = self.business_name.strip()
        if not 1 <= len(self.business_name) <= BUSINESS_NAME_MAXIMUM_LENGTH:
            raise BusinessError(
                "INVALID_BUSINESS_NAME",
                f"The business name must have between 1 and {BUSINESS_NAME_MAXIMUM_LENGTH} "
                "characters.",
                field="business_name",
            )
        self.address = blank_as_none(self.address)
        self.phone = blank_as_none(self.phone)

    @classmethod
    def register(cls, business_name: str, ruc: Ruc) -> "Store":
        """A new store starts active, with the initial credit conditions."""
        return cls(business_name, ruc, INITIAL_CONDITIONS)

    @property
    def is_active(self) -> bool:
        return self.status == StoreStatus.ACTIVE

    def update_profile(
        self,
        business_name: str,
        address: str | None,
        phone: str | None,
        default_conditions: CreditConditions,
    ) -> None:
        """Change what the store may edit. The RUC is its tax identity, so it never changes."""
        self.business_name = business_name
        self.address = address
        self.phone = phone
        self.default_conditions = default_conditions
        self.__post_init__()

    def deactivate(self) -> None:
        self.status = StoreStatus.INACTIVE

    def reactivate(self) -> None:
        self.status = StoreStatus.ACTIVE


def blank_as_none(text: str | None) -> str | None:
    return (text or "").strip() or None
