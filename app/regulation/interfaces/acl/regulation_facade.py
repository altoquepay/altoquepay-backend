"""The only way other bounded contexts may reach the regulation context.

Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class CurrentCap:
    max_tea: Decimal
    max_late_tea: Decimal
    valid_from: date
    valid_to: date | None


class RegulationFacade:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def validate_rates(self, tea: Decimal, late_tea: Decimal, on_date: date) -> None:
        """Raise RATE_ABOVE_BCRP_CAP (422), on the tea or late_tea field, if a rate is too high."""
        raise NotImplementedError

    async def get_current_cap(self, on_date: date) -> CurrentCap:
        """Return the cap in force on a date."""
        raise NotImplementedError
