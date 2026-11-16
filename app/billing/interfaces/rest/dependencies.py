from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.billing.application.command_services.payment_service import PaymentService
from app.billing.application.ports.account_directory import AccountDirectory
from app.billing.application.query_services.billing_query_service import BillingQueryService
from app.billing.infrastructure.acl.external_accounts import ExternalAccounts
from app.billing.infrastructure.acl.external_credit import ExternalCredit
from app.billing.infrastructure.persistence.billing_cycle_repository_impl import (
    BillingCycleRepositoryImpl,
)
from app.billing.infrastructure.persistence.payment_repository_impl import PaymentRepositoryImpl
from app.credit.interfaces.acl.credit_facade import CreditFacade
from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work


def get_account_directory(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> AccountDirectory:
    return ExternalAccounts(CustomersFacade(unit_of_work))


def get_payment_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    accounts: Annotated[AccountDirectory, Depends(get_account_directory)],
) -> PaymentService:
    return PaymentService(
        BillingCycleRepositoryImpl(unit_of_work.session),
        PaymentRepositoryImpl(unit_of_work.session),
        ExternalCredit(CreditFacade(unit_of_work)),
        accounts,
        unit_of_work,
        ZoneInfo(get_settings().app_timezone),
    )


def get_billing_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> BillingQueryService:
    return BillingQueryService(
        BillingCycleRepositoryImpl(unit_of_work.session),
        PaymentRepositoryImpl(unit_of_work.session),
        ExternalCredit(CreditFacade(unit_of_work)),
    )
