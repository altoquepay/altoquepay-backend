from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

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
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work


def get_business_today() -> date:
    """Return today in the time zone of the business, which may differ from the server's."""
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def get_bcrp_cap_command_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> BcrpCapCommandService:
    return BcrpCapCommandService(BcrpCapRepositoryImpl(unit_of_work.session), unit_of_work)


def get_bcrp_cap_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> BcrpCapQueryService:
    return BcrpCapQueryService(BcrpCapRepositoryImpl(unit_of_work.session))
