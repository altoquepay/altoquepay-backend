from typing import Annotated

from fastapi import Depends

from app.regulation.application.command_services.bcrp_cap_command_service import (
    BcrpCapCommandService,
)
from app.regulation.application.query_services.bcrp_cap_query_service import (
    BcrpCapQueryService,
)
from app.regulation.infrastructure.persistence.bcrp_cap_repository_impl import (
    BcrpCapRepositoryImpl,
)
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work


def get_bcrp_cap_command_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> BcrpCapCommandService:
    return BcrpCapCommandService(BcrpCapRepositoryImpl(unit_of_work.session), unit_of_work)


def get_bcrp_cap_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> BcrpCapQueryService:
    return BcrpCapQueryService(BcrpCapRepositoryImpl(unit_of_work.session))
