from abc import ABC, abstractmethod
from datetime import date

from app.shared.domain.value_objects import Rate


class RateCapChecker(ABC):
    """Checks rates against the legal caps of the BCRP, answered by the regulation context."""

    @abstractmethod
    async def check(self, tea: Rate, late_tea: Rate, on_date: date) -> None:
        """Raise RATE_ABOVE_BCRP_CAP if a rate is above the cap in force on the date.

        Raises NO_BCRP_CAP_IN_FORCE (409) if no cap is in force that day.
        """
