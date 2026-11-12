"""The only way other bounded contexts may reach the regulation context.

Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.regulation.application.query_services.bcrp_cap_query_service import (
    BcrpCapQueryService,
)
from app.regulation.infrastructure.persistence.bcrp_cap_repository_impl import (
    BcrpCapRepositoryImpl,
)
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class CurrentCap:
    max_tea: Decimal
    max_late_tea: Decimal
    valid_from: date
    valid_to: date


class RegulationFacade:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._query_service = BcrpCapQueryService(BcrpCapRepositoryImpl(unit_of_work.session))

    async def validate_rates(self, tea: Decimal, late_tea: Decimal, on_date: date) -> None:
        """Raise RATE_ABOVE_BCRP_CAP (422), on the tea or late_tea field, if a rate is too high.

        A rate equal to the cap is allowed. Raises NO_BCRP_CAP_IN_FORCE (409) if there is no cap.
        """
        cap = await self.get_current_cap(on_date)
        for field, rate, maximum in (
            ("tea", tea, cap.max_tea),
            ("late_tea", late_tea, cap.max_late_tea),
        ):
            if rate > maximum:
                readable_maximum = f"{maximum.normalize():f}"
                raise BusinessError(
                    "RATE_ABOVE_BCRP_CAP",
                    f"The rate exceeds the BCRP legal cap (max {readable_maximum}%).",
                    field=field,
                    details={"max": readable_maximum},
                )

    async def get_current_cap(self, on_date: date) -> CurrentCap:
        """Return the cap in force on a date. Raises NO_BCRP_CAP_IN_FORCE (409) if there is none."""
        cap = await self._query_service.get_in_force(on_date)
        return CurrentCap(
            max_tea=cap.max_tea.percent,
            max_late_tea=cap.max_late_tea.percent,
            valid_from=cap.valid_from,
            valid_to=cap.valid_to,
        )
