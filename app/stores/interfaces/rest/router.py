from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.shared.interfaces.rest.business_date import get_business_today
from app.shared.interfaces.rest.security import get_store_id
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
    StoreResource,
    UpdateStoreProfileResource,
)
from app.stores.interfaces.rest.transform.store_transform import (
    to_register_command,
    to_resource,
    to_update_profile_command,
)

router = APIRouter(tags=["Stores"])

StoreId = Annotated[int, Depends(get_store_id)]


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
