from app.shared.domain.value_objects import Ruc
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.model.commands.register_store_command import RegisterStoreCommand
from app.stores.interfaces.rest.resources.store_resources import (
    RegisterStoreResource,
    StoreResource,
)


def to_register_command(resource: RegisterStoreResource) -> RegisterStoreCommand:
    return RegisterStoreCommand(
        business_name=resource.business_name,
        ruc=Ruc(resource.ruc.strip()),
        admin_full_name=resource.full_name,
        admin_email=resource.email,
        admin_password=resource.password,
    )


def to_resource(store: Store) -> StoreResource:
    if store.id is None or store.registered_at is None:
        raise ValueError("Only a stored store has a resource.")
    conditions = store.default_conditions
    return StoreResource(
        id=store.id,
        business_name=store.business_name,
        ruc=store.ruc.value,
        address=store.address,
        phone=store.phone,
        status=store.status,
        registered_at=store.registered_at,
        default_cutoff_day=conditions.cutoff_day,
        default_payment_day=conditions.payment_day,
        default_tea=conditions.tea.percent,
        default_late_tea=conditions.late_tea.percent,
        default_max_weeks=conditions.max_weeks,
    )
