from typing import Annotated

from fastapi import Depends

from app.iam.interfaces.acl.iam_facade import IamFacade
from app.regulation.interfaces.acl.regulation_facade import RegulationFacade
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.stores.application.command_services.store_command_service import StoreCommandService
from app.stores.application.command_services.store_registration_service import (
    StoreRegistrationService,
)
from app.stores.application.query_services.store_query_service import StoreQueryService
from app.stores.infrastructure.acl.external_administrators import ExternalAdministrators
from app.stores.infrastructure.acl.external_rate_caps import ExternalRateCaps
from app.stores.infrastructure.persistence.store_repository_impl import StoreRepositoryImpl


def get_store_registration_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> StoreRegistrationService:
    return StoreRegistrationService(
        StoreRepositoryImpl(unit_of_work.session),
        ExternalAdministrators(IamFacade(unit_of_work)),
        unit_of_work,
    )


def get_store_command_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> StoreCommandService:
    return StoreCommandService(
        StoreRepositoryImpl(unit_of_work.session),
        ExternalRateCaps(RegulationFacade(unit_of_work)),
        unit_of_work,
    )


def get_store_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> StoreQueryService:
    return StoreQueryService(StoreRepositoryImpl(unit_of_work.session))
