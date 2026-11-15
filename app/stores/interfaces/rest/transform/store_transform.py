from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import CreditConditions, Rate, Ruc
from app.stores.application.query_services.store_query_service import StoreWithCustomers
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.model.commands.register_store_command import RegisterStoreCommand
from app.stores.domain.model.commands.update_store_profile_command import (
    UpdateStoreProfileCommand,
)
from app.stores.interfaces.rest.resources.store_resources import (
    RegisterStoreResource,
    StoreListItemResource,
    StoreResource,
    UpdateStoreProfileResource,
)


def to_register_command(resource: RegisterStoreResource) -> RegisterStoreCommand:
    return RegisterStoreCommand(
        business_name=resource.business_name,
        ruc=Ruc(resource.ruc.strip()),
        admin_full_name=resource.full_name,
        admin_email=resource.email,
        admin_password=resource.password,
    )


def to_update_profile_command(
    resource: UpdateStoreProfileResource, store_id: int
) -> UpdateStoreProfileCommand:
    return UpdateStoreProfileCommand(
        store_id=store_id,
        business_name=resource.business_name,
        address=resource.address,
        phone=resource.phone,
        default_conditions=to_default_conditions(resource),
    )


def to_default_conditions(resource: UpdateStoreProfileResource) -> CreditConditions:
    try:
        return CreditConditions(
            cutoff_day=resource.default_cutoff_day,
            payment_day=resource.default_payment_day,
            tea=Rate.from_percent(resource.default_tea),
            late_tea=Rate.from_percent(resource.default_late_tea),
            max_weeks=resource.default_max_weeks,
        )
    except BusinessError as error:
        # CreditConditions names the fields of an account; the store profile prefixes default_.
        if error.field is not None:
            error.field = f"default_{error.field}"
        raise


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


def to_list_item_resource(listed: StoreWithCustomers) -> StoreListItemResource:
    store = to_resource(listed.store)
    return StoreListItemResource(
        id=store.id,
        business_name=store.business_name,
        ruc=store.ruc,
        status=store.status,
        registered_at=store.registered_at,
        customers_count=listed.customers_count,
    )
