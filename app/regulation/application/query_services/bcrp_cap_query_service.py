from datetime import date

from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap
from app.regulation.domain.repositories.bcrp_cap_repository import BcrpCapRepository
from app.shared.domain.errors import BusinessError


class BcrpCapQueryService:
    def __init__(self, repository: BcrpCapRepository) -> None:
        self._repository = repository

    async def get_in_force(self, on_date: date) -> BcrpCap:
        cap = await self._repository.find_in_force(on_date)
        if cap is None:
            raise BusinessError(
                "NO_BCRP_CAP_IN_FORCE",
                f"No BCRP cap is in force on {on_date.isoformat()}. "
                "A system administrator must register it.",
                status=409,
            )
        return cap

    async def list_history(self) -> list[BcrpCap]:
        return await self._repository.list_all()
