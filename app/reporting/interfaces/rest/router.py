from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.reporting.application.query_services.customer_portal_service import (
    CustomerPortalService,
)
from app.reporting.application.query_services.store_report_service import StoreReportService
from app.reporting.interfaces.rest.dependencies import (
    get_customer_portal_service,
    get_store_report_service,
)
from app.reporting.interfaces.rest.resources.report_resources import (
    AccountOverviewResource,
    CustomerStoreResource,
    CycleStatementResource,
    DashboardResource,
    PeriodReportResource,
    PurchaseResource,
    PurchaseScheduleResource,
)
from app.reporting.interfaces.rest.transform import (
    to_customer_store,
    to_dashboard,
    to_overview,
    to_period_report,
    to_purchase,
    to_schedule,
    to_statement,
)
from app.shared.domain.value_objects import Role
from app.shared.interfaces.rest.business_date import get_business_today
from app.shared.interfaces.rest.security import CurrentUser, get_store_id, require_role

router = APIRouter(tags=["Reports"])

Customer = Annotated[CurrentUser, Depends(require_role(Role.CUSTOMER))]
StoreId = Annotated[int, Depends(get_store_id)]
Today = Annotated[date, Depends(get_business_today)]
Portal = Annotated[CustomerPortalService, Depends(get_customer_portal_service)]
Reports = Annotated[StoreReportService, Depends(get_store_report_service)]


@router.get("/me/stores")
async def list_my_stores(customer: Customer, portal: Portal) -> list[CustomerStoreResource]:
    """List the stores where the signed-in customer has an account."""
    return [to_customer_store(listed) for listed in await portal.my_stores(int(customer.user_id))]


@router.get("/me/stores/{store_id}/summary")
async def get_my_summary(
    store_id: int, customer: Customer, portal: Portal
) -> AccountOverviewResource:
    """Return the customer's credit in a store: limit, what is owed and what is left to pay.

    A store where the customer has no account answers 404.
    """
    return to_overview(await portal.overview(int(customer.user_id), store_id))


@router.get("/me/stores/{store_id}/cycles/{year}/{month}")
async def get_my_statement(
    store_id: int,
    year: Annotated[int, Path(ge=2000, le=2100)],
    month: Annotated[int, Path(ge=1, le=12)],
    customer: Customer,
    portal: Portal,
) -> CycleStatementResource:
    """Return the customer's statement of a month in a store, with late interest to today."""
    statement = await portal.statement(int(customer.user_id), store_id, year, month)
    return to_statement(statement)


@router.get("/me/stores/{store_id}/purchases")
async def list_my_purchases(
    store_id: int, customer: Customer, portal: Portal
) -> list[PurchaseResource]:
    """List the customer's purchases in a store, most recent first."""
    purchases = await portal.purchases(int(customer.user_id), store_id)
    return [to_purchase(purchase) for purchase in purchases]


@router.get("/me/stores/{store_id}/purchases/{purchase_id}/schedule")
async def get_my_schedule(
    store_id: int, purchase_id: int, customer: Customer, portal: Portal
) -> PurchaseScheduleResource:
    """Return one of the customer's purchases with its installments still to pay."""
    return to_schedule(await portal.schedule(int(customer.user_id), store_id, purchase_id))


@router.get("/dashboard")
async def get_dashboard(store_id: StoreId, reports: Reports, today: Today) -> DashboardResource:
    """Return the store's figures today: customers, debt, overdue installments, this month's
    purchases and payments, and the BCRP cap in force.
    """
    return to_dashboard(await reports.dashboard(store_id, today))


@router.get("/reports/summary")
async def get_report_summary(
    store_id: StoreId,
    reports: Reports,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> PeriodReportResource:
    """Add up the store's purchases and payments between two days, both included."""
    return to_period_report(await reports.period_report(store_id, from_date, to_date))
