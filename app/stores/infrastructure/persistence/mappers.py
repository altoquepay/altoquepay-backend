from app.shared.domain.value_objects import CreditConditions, Rate, Ruc
from app.stores.domain.model.aggregates.store import Store, StoreStatus
from app.stores.infrastructure.persistence.models import StoreModel


def to_domain(model: StoreModel) -> Store:
    return Store(
        business_name=model.business_name,
        ruc=Ruc(model.ruc),
        default_conditions=CreditConditions(
            cutoff_day=model.default_cutoff_day,
            payment_day=model.default_payment_day,
            tea=Rate.from_percent(model.default_tea),
            late_tea=Rate.from_percent(model.default_late_tea),
            max_weeks=model.default_max_weeks,
        ),
        address=model.address,
        phone=model.phone,
        status=StoreStatus(model.status),
        registered_at=model.registered_at,
        id=model.id,
    )


def copy_to_model(store: Store, model: StoreModel) -> StoreModel:
    conditions = store.default_conditions
    model.business_name = store.business_name
    model.ruc = store.ruc.value
    model.address = store.address
    model.phone = store.phone
    model.status = store.status.value
    model.default_cutoff_day = conditions.cutoff_day
    model.default_payment_day = conditions.payment_day
    model.default_tea = conditions.tea.percent
    model.default_late_tea = conditions.late_tea.percent
    model.default_max_weeks = conditions.max_weeks
    return model
