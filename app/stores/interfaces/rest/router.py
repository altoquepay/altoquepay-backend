from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.shared.domain.value_objects import Role
from app.shared.interfaces.rest.business_date import get_business_today
from app.shared.interfaces.rest.pagination import Page, PageParams
from app.shared.interfaces.rest.security import CurrentUser, get_store_id, require_role
from app.stores.application.command_services.store_command_service import StoreCommandService
from app.stores.application.command_services.store_registration_service import (
    StoreRegistrationService,
)
from app.stores.application.query_services.store_query_service import StoreQueryService
from app.stores.interfaces.rest.dependencies import (
    get_store_command_service,
    get_store_query_service,
    get_store_registration_service,
)
from app.stores.interfaces.rest.resources.store_resources import (
    RegisterStoreResource,
    StoreListItemResource,
    StoreResource,
    UpdateStoreProfileResource,
)
from app.stores.interfaces.rest.transform.store_transform import (
    to_list_item_resource,
    to_register_command,
    to_resource,
    to_update_profile_command,
)

router = APIRouter(tags=["Stores"])

StoreId = Annotated[int, Depends(get_store_id)]
SystemAdmin = Annotated[CurrentUser, Depends(require_role(Role.SYSTEM_ADMIN))]


@router.post("/stores/register", status_code=201)
async def register_store(
    resource: RegisterStoreResource,
    registration_service: Annotated[
        StoreRegistrationService, Depends(get_store_registration_service)
    ],
) -> StoreResource:
    """Register a bodega and its administrator. The administrator then signs in as usual."""
    store = await registration_service.register(to_register_command(resource))
    return to_resource(store)


@router.get("/store/profile")
async def get_store_profile(
    store_id: StoreId,
    query_service: Annotated[StoreQueryService, Depends(get_store_query_service)],
) -> StoreResource:
    """Return the profile and default credit conditions of the administrator's store."""
    return to_resource(await query_service.get(store_id))


@router.put("/store/profile")
async def update_store_profile(
    resource: UpdateStoreProfileResource,
    store_id: StoreId,
    command_service: Annotated[StoreCommandService, Depends(get_store_command_service)],
    today: Annotated[date, Depends(get_business_today)],
) -> StoreResource:
    """Replace the profile. The RUC never changes, and the rates must respect the BCRP caps."""
    command = to_update_profile_command(resource, store_id)
    return to_resource(await command_service.update_profile(command, today))


@router.get("/admin/stores")
async def list_stores(
    _admin: SystemAdmin,
    params: Annotated[PageParams, Query()],
    query_service: Annotated[StoreQueryService, Depends(get_store_query_service)],
) -> Page[StoreListItemResource]:
    """List the stores, the most recently registered first, with their number of customers."""
    listed, total = await query_service.list_page(params.offset, params.size)
    return Page(
        items=[to_list_item_resource(item) for item in listed],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.patch("/admin/stores/{store_id}/deactivate")
async def deactivate_store(
    store_id: int,
    _admin: SystemAdmin,
    command_service: Annotated[StoreCommandService, Depends(get_store_command_service)],
) -> StoreResource:
    """Block the store at once: its administrator can no longer sign in or keep working."""
    return to_resource(await command_service.deactivate(store_id))


@router.patch("/admin/stores/{store_id}/reactivate")
async def reactivate_store(
    store_id: int,
    _admin: SystemAdmin,
    command_service: Annotated[StoreCommandService, Depends(get_store_command_service)],
) -> StoreResource:
    """Let the administrator of the store sign in and work again."""
    return to_resource(await command_service.reactivate(store_id))
