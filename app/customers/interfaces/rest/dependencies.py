from typing import Annotated

from fastapi import Depends

from app.customers.application.command_services.account_command_service import (
    AccountCommandService,
)
from app.customers.application.query_services.account_query_service import AccountQueryService
from app.customers.infrastructure.acl.external_rate_caps import ExternalRateCaps
from app.customers.infrastructure.acl.external_stores import ExternalStores
from app.customers.infrastructure.acl.external_users import ExternalUsers
from app.customers.infrastructure.persistence.customer_repository_impl import (
    CustomerRepositoryImpl,
)
from app.customers.infrastructure.persistence.store_customer_repository_impl import (
    StoreCustomerRepositoryImpl,
)
from app.iam.interfaces.acl.iam_facade import IamFacade
from app.regulation.interfaces.acl.regulation_facade import RegulationFacade
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.stores.interfaces.acl.stores_facade import StoresFacade


def get_account_command_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> AccountCommandService:
    return AccountCommandService(
        CustomerRepositoryImpl(unit_of_work.session),
        StoreCustomerRepositoryImpl(unit_of_work.session),
        ExternalStores(StoresFacade(unit_of_work)),
        ExternalRateCaps(RegulationFacade(unit_of_work)),
        ExternalUsers(IamFacade(unit_of_work)),
        unit_of_work,
    )


def get_account_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> AccountQueryService:
    return AccountQueryService(
        CustomerRepositoryImpl(unit_of_work.session),
        StoreCustomerRepositoryImpl(unit_of_work.session),
    )
