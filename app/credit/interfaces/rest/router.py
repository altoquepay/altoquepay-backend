from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.credit.application.command_services.purchase_registration_service import (
    PurchaseRegistrationService,
)
from app.credit.application.query_services.purchase_query_service import PurchaseQueryService
from app.credit.domain.model.aggregates.purchase import InstallmentStatus, PaymentMode
from app.credit.domain.repositories.purchase_repository import PurchaseFilter
from app.credit.interfaces.rest.dependencies import (
    get_purchase_query_service,
    get_purchase_registration_service,
)
from app.credit.interfaces.rest.resources.purchase_resources import (
    InstallmentListItemResource,
    InstallmentResource,
    PurchaseDetailResource,
    PurchaseResource,
    RegisterPurchaseResource,
)
from app.credit.interfaces.rest.transform.purchase_transform import (
    to_detail_resource,
    to_installment_list_item,
    to_installment_resource,
    to_register_command,
    to_resource,
)
from app.shared.interfaces.rest.business_date import get_business_now, get_business_today
from app.shared.interfaces.rest.pagination import Page, PageParams
from app.shared.interfaces.rest.security import CurrentUser, get_current_user, get_store_id

router = APIRouter(tags=["Purchases"])

StoreId = Annotated[int, Depends(get_store_id)]
User = Annotated[CurrentUser, Depends(get_current_user)]
Now = Annotated[datetime, Depends(get_business_now)]
Today = Annotated[date, Depends(get_business_today)]
QueryService = Annotated[PurchaseQueryService, Depends(get_purchase_query_service)]
RegistrationService = Annotated[
    PurchaseRegistrationService, Depends(get_purchase_registration_service)
]


@router.post("/purchases/simulate")
async def simulate_purchase(
    resource: RegisterPurchaseResource,
    store_id: StoreId,
    user: User,
    registration_service: RegistrationService,
    now: Now,
) -> PurchaseDetailResource:
    """Calculate a purchase and its schedule with every check of the registration; save nothing."""
    command = to_register_command(resource, store_id, int(user.user_id))
    return to_detail_resource(await registration_service.simulate(command, now), now.date())


@router.post("/purchases", status_code=201)
async def register_purchase(
    resource: RegisterPurchaseResource,
    store_id: StoreId,
    user: User,
    registration_service: RegistrationService,
    now: Now,
) -> PurchaseDetailResource:
    """Register a purchase on credit. The server sets the list prices and the account's rates."""
    command = to_register_command(resource, store_id, int(user.user_id))
    return to_detail_resource(await registration_service.register(command, now), now.date())


@router.patch("/purchases/{purchase_id}/void")
async def void_purchase(
    purchase_id: int,
    store_id: StoreId,
    user: User,
    registration_service: RegistrationService,
    now: Now,
) -> PurchaseDetailResource:
    """Void a purchase registered by mistake. Its installments are cancelled.

    Only while nothing of it is paid (PURCHASE_NOT_VOIDABLE, 409) and its cycle is still open
    (CYCLE_CLOSED, 409): a closed statement is never changed.
    """
    purchase = await registration_service.void(store_id, purchase_id, int(user.user_id), now)
    return to_detail_resource(purchase, now.date())


@router.get("/purchases")
async def list_purchases(
    store_id: StoreId,
    params: Annotated[PageParams, Query()],
    query_service: QueryService,
    customer_id: int | None = None,
    mode: PaymentMode | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> Page[PurchaseResource]:
    """List the store's purchases, most recent first. from and to are days in Lima, inclusive."""
    purchase_filter = PurchaseFilter(customer_id, mode, from_date, to_date)
    purchases, total = await query_service.list_page(
        store_id, purchase_filter, params.offset, params.size
    )
    return Page(
        items=[to_resource(purchase) for purchase in purchases],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/purchases/{purchase_id}")
async def get_purchase(
    purchase_id: int, store_id: StoreId, query_service: QueryService, today: Today
) -> PurchaseDetailResource:
    """Return a purchase with its items and installments."""
    return to_detail_resource(await query_service.get(store_id, purchase_id), today)


@router.get("/purchases/{purchase_id}/schedule")
async def get_purchase_schedule(
    purchase_id: int, store_id: StoreId, query_service: QueryService, today: Today
) -> list[InstallmentResource]:
    """Return the installments of a purchase, with their status today. Empty for single date."""
    purchase = await query_service.get(store_id, purchase_id)
    return [to_installment_resource(installment, today) for installment in purchase.installments]


@router.get("/installments")
async def list_installments(
    store_id: StoreId,
    params: Annotated[PageParams, Query()],
    query_service: QueryService,
    today: Today,
    status: InstallmentStatus | None = None,
    due_before: date | None = None,
) -> Page[InstallmentListItemResource]:
    """List the store's installments by due date. due_before includes that day."""
    entries, total = await query_service.list_installments(
        store_id, status, due_before, today, params.offset, params.size
    )
    return Page(
        items=[to_installment_list_item(entry, today) for entry in entries],
        total=total,
        page=params.page,
        size=params.size,
    )
