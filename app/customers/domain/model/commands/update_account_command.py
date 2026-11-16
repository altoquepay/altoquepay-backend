from dataclasses import dataclass

from app.shared.domain.value_objects import CreditConditions, Money


@dataclass(frozen=True)
class UpdateAccountCommand:
    store_id: int
    account_id: int
    first_names: str
    last_names: str
    phone: str | None
    address: str | None
    credit_limit: Money
    conditions: CreditConditions
