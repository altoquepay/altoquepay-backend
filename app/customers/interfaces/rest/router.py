from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.customers.application.command_services.account_command_service import (
    AccountCommandService,
)
from app.customers.application.query_services.account_query_service import AccountQueryService
from app.customers.domain.model.aggregates.store_customer import AccountStatus
from app.customers.domain.repositories.store_customer_repository import AccountFilter
from app.customers.interfaces.rest.dependencies import (
    get_account_command_service,
    get_account_query_service,
)
from app.customers.interfaces.rest.resources.customer_resources import (
    AccessCodeResource,
    CustomerAccountResource,
    LinkStoreResource,
    OpenAccountResource,
    OpenedAccountResource,
    PersonLookupResource,
    TrustStoreResource,
    UpdateAccountResource,
)
from app.customers.interfaces.rest.transform.customer_transform import (
    to_access_code_resource,
    to_lookup_resource,
    to_open_command,
    to_opened_resource,
    to_resource,
    to_update_command,
)
from app.shared.domain.value_objects import Dni, Role
from app.shared.interfaces.rest.business_date import get_business_now, get_business_today
from app.shared.interfaces.rest.pagination import Page, PageParams
from app.shared.interfaces.rest.security import (
    CurrentUser,
    get_customer,
    get_store_id,
    require_role,
)

router = APIRouter(prefix="/customers", tags=["Customers"])
# Outside /customers: the customer's own portal lives under /me, and support under /admin.
portal_router = APIRouter(tags=["Customers"])

StoreId = Annotated[int, Depends(get_store_id)]
Customer = Annotated[CurrentUser, Depends(get_customer)]
SystemAdmin = Annotated[CurrentUser, Depends(require_role(Role.SYSTEM_ADMIN))]
Today = Annotated[date, Depends(get_business_today)]
Now = Annotated[datetime, Depends(get_business_now)]
QueryService = Annotated[AccountQueryService, Depends(get_account_query_service)]
CommandService = Annotated[AccountCommandService, Depends(get_account_command_service)]


@router.get("")
async def list_customers(
    store_id: StoreId,
    params: Annotated[PageParams, Query()],
    query_service: QueryService,
    search: Annotated[str | None, Query(max_length=100)] = None,
    status: AccountStatus | None = None,
) -> Page[CustomerAccountResource]:
    """List the store's customer accounts, newest first. search matches the DNI or the names."""
    listed, total = await query_service.list_page(
        store_id, AccountFilter(search, status), params.offset, params.size
    )
    return Page(
        items=[to_resource(found) for found in listed],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/lookup")
async def lookup_customer(
    store_id: StoreId,
    query_service: QueryService,
    dni: Annotated[str, Query(max_length=8)],
) -> PersonLookupResource:
    """Find a person by DNI before opening their account, without what other stores typed.

    404 if nobody has the DNI yet. account_id is set when the store already has their account.
    notice is PERSON_HAS_ACCOUNT, not an error, when the person already buys in another store.
    """
    return to_lookup_resource(await query_service.lookup(store_id, Dni(dni.strip())))


@router.post("", status_code=201)
async def open_account(
    resource: OpenAccountResource,
    store_id: StoreId,
    command_service: CommandService,
    today: Today,
    now: Now,
) -> OpenedAccountResource:
    """Open the store's account for a person. Missing conditions take the store's defaults.

    The access code comes back only this once. Hand it to the customer: the account stays out
    of their portal until they redeem it.
    """
    opened = await command_service.open(to_open_command(resource, store_id), today, now)
    return to_opened_resource(opened)


@router.get("/{account_id}")
async def get_customer(
    account_id: int, store_id: StoreId, query_service: QueryService
) -> CustomerAccountResource:
    """Return an account of the store with the person's data."""
    return to_resource(await query_service.get(store_id, account_id))


@router.put("/{account_id}")
async def update_customer(
    account_id: int,
    resource: UpdateAccountResource,
    store_id: StoreId,
    command_service: CommandService,
    today: Today,
) -> CustomerAccountResource:
    """Replace the person's data and the account terms. The DNI never changes.

    The person's data is shared by every store where they buy.
    """
    command = to_update_command(resource, store_id, account_id)
    return to_resource(await command_service.update(command, today))


@router.patch("/{account_id}/deactivate")
async def deactivate_customer(
    account_id: int, store_id: StoreId, command_service: CommandService
) -> CustomerAccountResource:
    """Stop new purchases on credit in this store. Past purchases and payments stay."""
    return to_resource(await command_service.deactivate(store_id, account_id))


@router.post("/{account_id}/access-code")
async def issue_access_code(
    account_id: int, store_id: StoreId, command_service: CommandService, now: Now
) -> AccessCodeResource:
    """Give the customer a new access code, shown only this once. It replaces the previous one.

    For a customer who forgot their password or still has to link this store. Nothing changes
    for them until they redeem it.
    """
    access_code = await command_service.issue_access_code(store_id, account_id, now)
    return to_access_code_resource(access_code)


@portal_router.post("/me/stores/link", status_code=204)
async def link_my_store(
    resource: LinkStoreResource, customer: Customer, command_service: CommandService, now: Now
) -> None:
    """Add a store to the signed-in customer's portal with the access code it handed them."""
    await command_service.link_with_code(int(customer.user_id), resource.code, now)


@portal_router.post("/admin/customers/trusted-store", status_code=204)
async def trust_store(
    resource: TrustStoreResource, _admin: SystemAdmin, command_service: CommandService
) -> None:
    """Let only this store restore the customer's access, once support confirmed it with them.

    For a customer locked out by a store they do not trust. Their other stores leave the portal
    and can no longer restore it; the customer links them again with a new code.
    """
    await command_service.trust_store(Dni(resource.dni.strip()), resource.store_id)
