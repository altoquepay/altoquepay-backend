from typing import Annotated

from fastapi import Depends

from app.iam.interfaces.acl.iam_facade import IamFacade
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.stores.application.command_services.store_registration_service import (
    StoreRegistrationService,
)
from app.stores.infrastructure.acl.external_administrators import ExternalAdministrators
from app.stores.infrastructure.persistence.store_repository_impl import StoreRepositoryImpl


def get_store_registration_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> StoreRegistrationService:
    return StoreRegistrationService(
        StoreRepositoryImpl(unit_of_work.session),
        ExternalAdministrators(IamFacade(unit_of_work)),
        unit_of_work,
    )
