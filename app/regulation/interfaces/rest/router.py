from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.regulation.application.command_services.bcrp_cap_command_service import (
    BcrpCapCommandService,
)
from app.regulation.application.query_services.bcrp_cap_query_service import (
    BcrpCapQueryService,
)
from app.regulation.interfaces.rest.dependencies import (
    get_bcrp_cap_command_service,
    get_bcrp_cap_query_service,
    get_business_today,
)
from app.regulation.interfaces.rest.resources.bcrp_cap_resources import (
    BcrpCapResource,
    RegisterBcrpCapResource,
)
from app.regulation.interfaces.rest.transform.bcrp_cap_transform import (
    to_register_command,
    to_resource,
)
from app.shared.domain.value_objects import Role
from app.shared.interfaces.rest.security import CurrentUser, get_current_user, require_role

router = APIRouter(tags=["BCRP caps"])

SystemAdmin = Annotated[CurrentUser, Depends(require_role(Role.SYSTEM_ADMIN))]


@router.get("/admin/bcrp-caps")
async def list_bcrp_caps(
    _admin: SystemAdmin,
    query_service: Annotated[BcrpCapQueryService, Depends(get_bcrp_cap_query_service)],
) -> list[BcrpCapResource]:
    """List every BCRP cap, the most recent first."""
    # shortcut: not paginated because the BCRP sets two caps a year; paginate if that changes.
    return [to_resource(cap) for cap in await query_service.list_history()]


@router.post("/admin/bcrp-caps", status_code=201)
async def register_bcrp_cap(
    resource: RegisterBcrpCapResource,
    admin: SystemAdmin,
    command_service: Annotated[BcrpCapCommandService, Depends(get_bcrp_cap_command_service)],
) -> BcrpCapResource:
    """Register the cap of a validity period that overlaps no other."""
    command = to_register_command(resource, registered_by=int(admin.user_id))
    return to_resource(await command_service.register(command))


@router.get("/bcrp-caps/current")
async def get_current_bcrp_cap(
    _user: Annotated[CurrentUser, Depends(get_current_user)],
    query_service: Annotated[BcrpCapQueryService, Depends(get_bcrp_cap_query_service)],
    today: Annotated[date, Depends(get_business_today)],
) -> BcrpCapResource:
    """Return the cap in force today, so forms can validate rates before saving."""
    return to_resource(await query_service.get_in_force(today))
