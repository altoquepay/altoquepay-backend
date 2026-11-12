from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap
from app.regulation.domain.model.commands.register_bcrp_cap_command import (
    RegisterBcrpCapCommand,
)
from app.regulation.interfaces.rest.resources.bcrp_cap_resources import (
    BcrpCapResource,
    RegisterBcrpCapResource,
)
from app.shared.domain.value_objects import Rate


def to_register_command(
    resource: RegisterBcrpCapResource, registered_by: int
) -> RegisterBcrpCapCommand:
    return RegisterBcrpCapCommand(
        max_tea=Rate.from_percent(resource.max_tea),
        valid_from=resource.valid_from,
        valid_to=resource.valid_to,
        registered_by=registered_by,
    )


def to_resource(cap: BcrpCap) -> BcrpCapResource:
    if cap.id is None:
        raise ValueError("Only a stored cap has a resource.")
    return BcrpCapResource(
        id=cap.id,
        max_tea=cap.max_tea.percent,
        max_late_tea=cap.max_late_tea.percent,
        valid_from=cap.valid_from,
        valid_to=cap.valid_to,
    )
