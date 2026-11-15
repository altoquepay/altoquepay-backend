from typing import Annotated

from fastapi import APIRouter, Depends

from app.stores.application.command_services.store_registration_service import (
    StoreRegistrationService,
)
from app.stores.interfaces.rest.dependencies import get_store_registration_service
from app.stores.interfaces.rest.resources.store_resources import (
    RegisterStoreResource,
    StoreResource,
)
from app.stores.interfaces.rest.transform.store_transform import to_register_command, to_resource

router = APIRouter(tags=["Stores"])


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
