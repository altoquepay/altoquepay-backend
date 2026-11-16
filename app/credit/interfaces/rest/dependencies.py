from typing import Annotated

from fastapi import Depends

from app.billing.interfaces.acl.billing_facade import BillingFacade
from app.catalog.interfaces.acl.catalog_facade import CatalogFacade
from app.credit.application.command_services.purchase_registration_service import (
    PurchaseRegistrationService,
)
from app.credit.application.query_services.purchase_query_service import PurchaseQueryService
from app.credit.infrastructure.acl.external_billing import ExternalBilling
from app.credit.infrastructure.acl.external_catalog import ExternalCatalog
from app.credit.infrastructure.acl.external_customers import ExternalCustomers
from app.credit.infrastructure.persistence.purchase_repository_impl import PurchaseRepositoryImpl
from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work


def get_purchase_registration_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PurchaseRegistrationService:
    return PurchaseRegistrationService(
        PurchaseRepositoryImpl(unit_of_work.session),
        ExternalCustomers(CustomersFacade(unit_of_work)),
        ExternalCatalog(CatalogFacade(unit_of_work)),
        ExternalBilling(BillingFacade(unit_of_work)),
        unit_of_work,
    )


def get_purchase_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PurchaseQueryService:
    return PurchaseQueryService(PurchaseRepositoryImpl(unit_of_work.session))
