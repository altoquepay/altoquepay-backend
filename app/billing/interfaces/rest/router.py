from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.billing.application.command_services.payment_service import PaymentService
from app.billing.application.ports.account_directory import AccountDirectory
from app.billing.application.ports.store_directory import StoreDirectory
from app.billing.application.query_services.billing_query_service import BillingQueryService
from app.billing.domain.model.aggregates.billing_cycle import CycleStatus
from app.billing.domain.model.aggregates.payment import PaymentKind
from app.billing.domain.repositories.billing_cycle_repository import CycleFilter
from app.billing.domain.repositories.payment_repository import PaymentFilter
from app.billing.infrastructure.pdf.statement_pdf import render_statement
from app.billing.interfaces.rest.dependencies import (
    get_account_directory,
    get_billing_query_service,
    get_payment_service,
    get_store_directory,
)
from app.billing.interfaces.rest.resources.billing_resources import (
    CycleResource,
    PaymentQuoteResource,
    PaymentResource,
    PaymentTargetResource,
    RegisterPaymentResource,
    StatementResource,
)
from app.billing.interfaces.rest.transform.billing_transform import (
    to_cycle_resource,
    to_payment_resource,
    to_quote_resource,
    to_statement_resource,
    to_target,
)
from app.shared.domain.value_objects import Money
from app.shared.interfaces.rest.business_date import get_business_now, get_business_today
from app.shared.interfaces.rest.pagination import Page, PageParams
from app.shared.interfaces.rest.security import CurrentUser, get_current_user, get_store_id

router = APIRouter(tags=["Billing"])

StoreId = Annotated[int, Depends(get_store_id)]
User = Annotated[CurrentUser, Depends(get_current_user)]
Today = Annotated[date, Depends(get_business_today)]
Now = Annotated[datetime, Depends(get_business_now)]
Payments = Annotated[PaymentService, Depends(get_payment_service)]
Queries = Annotated[BillingQueryService, Depends(get_billing_query_service)]
Accounts = Annotated[AccountDirectory, Depends(get_account_directory)]
Stores = Annotated[StoreDirectory, Depends(get_store_directory)]


@router.get("/cycles")
async def list_cycles(
    store_id: StoreId,
    params: Annotated[PageParams, Query()],
    queries: Queries,
    today: Today,
    now: Now,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    status: CycleStatus | None = None,
    customer_id: int | None = None,
) -> Page[CycleResource]:
    """List the store's cycles, the most recent period first.

    Cycles whose cutoff day ended are closed first. OVERDUE means closed and past its payment date.
    """
    cycle_filter = CycleFilter(year, month, status, customer_id)
    cycles, total = await queries.list_cycles(
        store_id, cycle_filter, today, now, params.offset, params.size
    )
    return Page(
        items=[to_cycle_resource(cycle, today) for cycle in cycles],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/customers/{customer_id}/cycles/{year}/{month}")
async def get_cycle_statement(
    customer_id: int,
    year: Annotated[int, Path(ge=2000, le=2100)],
    month: Annotated[int, Path(ge=1, le=12)],
    store_id: StoreId,
    queries: Queries,
    accounts: Accounts,
    today: Today,
    now: Now,
) -> StatementResource:
    """Return the statement of an account's month, with late interest up to today if overdue."""
    statement = await queries.get_store_statement(
        accounts, store_id, customer_id, year, month, today, now
    )
    return to_statement_resource(statement)


@router.get(
    "/customers/{customer_id}/cycles/{year}/{month}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def get_cycle_statement_pdf(
    customer_id: int,
    year: Annotated[int, Path(ge=2000, le=2100)],
    month: Annotated[int, Path(ge=1, le=12)],
    store_id: StoreId,
    queries: Queries,
    accounts: Accounts,
    stores: Stores,
    today: Today,
    now: Now,
) -> Response:
    """Return the same statement as a PDF to download."""
    statement = await queries.get_store_statement(
        accounts, store_id, customer_id, year, month, today, now
    )
    holder = await accounts.get_holder(customer_id)
    store_name = await stores.business_name(store_id)
    return Response(
        render_statement(statement, store_name, holder, now),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="estado-{year}-{month:02d}.pdf"'},
    )


@router.post("/payments/quote")
async def quote_payment(
    resource: PaymentTargetResource,
    store_id: StoreId,
    payments: Payments,
    today: Today,
    now: Now,
) -> PaymentQuoteResource:
    """Calculate what a payment made today takes, without saving it."""
    return to_quote_resource(await payments.quote(store_id, to_target(resource), today, now))


@router.post("/payments", status_code=201)
async def register_payment(
    resource: RegisterPaymentResource,
    store_id: StoreId,
    user: User,
    payments: Payments,
    today: Today,
    now: Now,
) -> PaymentResource:
    """Register a payment made today and mark what it paid.

    amount must be exactly the quoted total: there are no partial payments. It is applied to
    late interest first, then ordinary interest, then principal.
    """
    payment = await payments.register(
        store_id, to_target(resource), Money(resource.amount), int(user.user_id), today, now
    )
    return to_payment_resource(payment)


@router.get("/payments")
async def list_payments(
    store_id: StoreId,
    params: Annotated[PageParams, Query()],
    queries: Queries,
    customer_id: int | None = None,
    kind: PaymentKind | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> Page[PaymentResource]:
    """List the store's payments, most recent first. from and to are inclusive days."""
    payment_filter = PaymentFilter(customer_id, kind, from_date, to_date)
    listed, total = await queries.list_store_payments(
        store_id, payment_filter, params.offset, params.size
    )
    return Page(
        items=[to_payment_resource(payment) for payment in listed],
        total=total,
        page=params.page,
        size=params.size,
    )
