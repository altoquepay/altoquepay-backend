from dataclasses import dataclass

from app.shared.domain.value_objects import CreditConditions


@dataclass(frozen=True)
class UpdateStoreProfileCommand:
    store_id: int
    business_name: str
    address: str | None
    phone: str | None
    default_conditions: CreditConditions
