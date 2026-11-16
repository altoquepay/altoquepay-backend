from datetime import date

from app.customers.application.ports.rate_cap_checker import RateCapChecker
from app.regulation.interfaces.acl.regulation_facade import RegulationFacade
from app.shared.domain.value_objects import Rate


class ExternalRateCaps(RateCapChecker):
    def __init__(self, regulation_facade: RegulationFacade) -> None:
        self._regulation_facade = regulation_facade

    async def check(self, tea: Rate, late_tea: Rate, on_date: date) -> None:
        await self._regulation_facade.validate_rates(tea.percent, late_tea.percent, on_date)
