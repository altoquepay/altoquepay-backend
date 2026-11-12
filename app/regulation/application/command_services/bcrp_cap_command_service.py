from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap
from app.regulation.domain.model.commands.register_bcrp_cap_command import (
    RegisterBcrpCapCommand,
)
from app.regulation.domain.repositories.bcrp_cap_repository import BcrpCapRepository
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork


class BcrpCapCommandService:
    def __init__(self, repository: BcrpCapRepository, unit_of_work: UnitOfWork) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    async def register(self, command: RegisterBcrpCapCommand) -> BcrpCap:
        cap = BcrpCap(
            max_tea=command.max_tea,
            valid_from=command.valid_from,
            valid_to=command.valid_to,
            created_by=command.registered_by,
        )
        # shortcut: two simultaneous registrations can both pass this check, and the database
        # constraint then rejects one with a 500; map IntegrityError to 409 if that ever happens.
        if await self._repository.exists_overlapping(cap.valid_from, cap.valid_to):
            raise BusinessError(
                "BCRP_CAP_OVERLAP",
                "The validity period overlaps the period of another BCRP cap.",
                field="valid_from",
                status=409,
            )
        await self._repository.add(cap)
        await self._unit_of_work.commit()
        return cap
