from typing import Annotated

from fastapi import Depends

from app.billing.interfaces.acl.billing_facade import BillingFacade
from app.credit.interfaces.acl.credit_facade import CreditFacade
from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.regulation.interfaces.acl.regulation_facade import RegulationFacade
from app.reporting.application.query_services.customer_portal_service import (
    CustomerPortalService,
)
from app.reporting.application.query_services.store_report_service import StoreReportService
from app.reporting.infrastructure.acl.external_readers import (
    ExternalBilling,
    ExternalCredit,
    ExternalCustomers,
    ExternalRateCaps,
    ExternalStores,
)
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.stores.interfaces.acl.stores_facade import StoresFacade


def get_customer_portal_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> CustomerPortalService:
    return CustomerPortalService(
        ExternalCustomers(CustomersFacade(unit_of_work)),
        ExternalStores(StoresFacade(unit_of_work)),
        ExternalCredit(CreditFacade(unit_of_work)),
        ExternalBilling(BillingFacade(unit_of_work)),
    )


def get_store_report_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> StoreReportService:
    return StoreReportService(
        ExternalCustomers(CustomersFacade(unit_of_work)),
        ExternalCredit(CreditFacade(unit_of_work)),
        ExternalBilling(BillingFacade(unit_of_work)),
        ExternalRateCaps(RegulationFacade(unit_of_work)),
    )
