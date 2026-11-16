from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.credit.application.command_services.purchase_registration_service import (
    PurchaseRegistrationService,
)
from app.credit.interfaces.rest.dependencies import get_purchase_registration_service
from app.credit.interfaces.rest.resources.purchase_resources import (
    PurchaseDetailResource,
    RegisterPurchaseResource,
)
from app.credit.interfaces.rest.transform.purchase_transform import (
    to_detail_resource,
    to_register_command,
)
from app.shared.interfaces.rest.business_date import get_business_now
from app.shared.interfaces.rest.security import CurrentUser, get_current_user, get_store_id

router = APIRouter(tags=["Purchases"])

StoreId = Annotated[int, Depends(get_store_id)]
User = Annotated[CurrentUser, Depends(get_current_user)]
Now = Annotated[datetime, Depends(get_business_now)]
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
