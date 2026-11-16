from dataclasses import dataclass
from decimal import Decimal

from app.shared.domain.value_objects import Dni, Money


@dataclass(frozen=True)
class OpenAccountCommand:
    """Conditions left as None take the store's defaults. Names are needed only for a new DNI."""

    store_id: int
    dni: Dni
    first_names: str | None
    last_names: str | None
    phone: str | None
    address: str | None
    credit_limit: Money
    cutoff_day: int | None = None
    payment_day: int | None = None
    tea: Decimal | None = None
    late_tea: Decimal | None = None
    max_weeks: int | None = None
