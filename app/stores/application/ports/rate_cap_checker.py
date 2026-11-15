from abc import ABC, abstractmethod
from datetime import date

from app.shared.domain.value_objects import Rate


class RateCapChecker(ABC):
    """Checks rates against the legal caps of the BCRP, answered by the regulation context."""

    @abstractmethod
    async def check(self, tea: Rate, late_tea: Rate, on_date: date) -> None:
        """Raise RATE_ABOVE_BCRP_CAP on default_tea or default_late_tea if a rate is too high."""
