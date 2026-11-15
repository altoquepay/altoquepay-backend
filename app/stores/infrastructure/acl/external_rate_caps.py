from datetime import date

from app.regulation.interfaces.acl.regulation_facade import RegulationFacade
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Rate
from app.stores.application.ports.rate_cap_checker import RateCapChecker


class ExternalRateCaps(RateCapChecker):
    def __init__(self, regulation_facade: RegulationFacade) -> None:
        self._regulation_facade = regulation_facade

    async def check(self, tea: Rate, late_tea: Rate, on_date: date) -> None:
        try:
            await self._regulation_facade.validate_rates(tea.percent, late_tea.percent, on_date)
        except BusinessError as error:
            # The facade names tea and late_tea; the store profile calls them default_*.
            if error.field is not None:
                error.field = f"default_{error.field}"
            raise
