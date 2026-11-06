"""The only way other bounded contexts may reach the stores context.

Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from decimal import Decimal

from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class StoreSummary:
    store_id: int
    business_name: str
    status: str


@dataclass(frozen=True)
class DefaultConditions:
    cutoff_day: int
    payment_day: int
    tea: Decimal
    late_tea: Decimal
    max_weeks: int


class StoresFacade:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def get_store_status(self, store_id: int) -> StoreSummary:
        """Return the status of a store, with the name its customers see in their portal."""
        raise NotImplementedError

    async def get_default_conditions(self, store_id: int) -> DefaultConditions:
        """Return the conditions a new customer gets when the store sets none."""
        raise NotImplementedError
