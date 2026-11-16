from datetime import date
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
    CredentialsResource,
    CustomerAccountResource,
    OpenAccountResource,
    OpenedAccountResource,
    PersonLookupResource,
    UpdateAccountResource,
)
from app.customers.interfaces.rest.transform.customer_transform import (
    to_credentials_resource,
    to_lookup_resource,
    to_open_command,
    to_opened_resource,
    to_resource,
    to_update_command,
)
from app.shared.domain.value_objects import Dni
from app.shared.interfaces.rest.business_date import get_business_today
from app.shared.interfaces.rest.pagination import Page, PageParams
from app.shared.interfaces.rest.security import get_store_id

router = APIRouter(prefix="/customers", tags=["Customers"])

StoreId = Annotated[int, Depends(get_store_id)]
Today = Annotated[date, Depends(get_business_today)]
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
    """Find a person by DNI before opening their account, to fill in the form.

    404 if nobody has the DNI yet. notice is PERSON_HAS_ACCOUNT, not an error, when the person
    already buys in another store.
    """
    return to_lookup_resource(await query_service.lookup(store_id, Dni(dni.strip())))


@router.post("", status_code=201)
async def open_account(
    resource: OpenAccountResource,
    store_id: StoreId,
    command_service: CommandService,
    today: Today,
) -> OpenedAccountResource:
    """Open the store's account for a person. Missing conditions take the store's defaults.

    The credentials come back only when the DNI is new, and only this once.
    """
    opened = await command_service.open(to_open_command(resource, store_id), today)
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


@router.post("/{account_id}/reset-password")
async def reset_customer_password(
    account_id: int, store_id: StoreId, command_service: CommandService
) -> CredentialsResource:
    """Give the customer a new temporary password, shown only this once."""
    credentials = await command_service.reset_password(store_id, account_id)
    return to_credentials_resource(credentials)
