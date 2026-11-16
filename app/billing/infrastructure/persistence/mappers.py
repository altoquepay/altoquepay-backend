from decimal import Decimal

from app.billing.domain.model.aggregates.billing_cycle import BillingCycle, CycleStatus
from app.billing.infrastructure.persistence.models import BillingCycleModel
from app.shared.domain.value_objects import Money


def money_or_none(amount: Decimal | None) -> Money | None:
    return Money(amount) if amount is not None else None


def amount_or_none(money: Money | None) -> Decimal | None:
    return money.amount if money is not None else None


def to_domain(model: BillingCycleModel) -> BillingCycle:
    return BillingCycle(
        store_customer_id=model.store_customer_id,
        year=model.year,
        month=model.month,
        cutoff_date=model.cutoff_date,
        payment_date=model.payment_date,
        status=CycleStatus(model.status),
        closed_at=model.closed_at,
        capital=money_or_none(model.capital),
        ordinary_interest=money_or_none(model.ordinary_interest),
        late_interest=money_or_none(model.late_interest),
        total=money_or_none(model.total),
        id=model.id,
    )


def to_model(cycle: BillingCycle) -> BillingCycleModel:
    return BillingCycleModel(
        store_customer_id=cycle.store_customer_id,
        year=cycle.year,
        month=cycle.month,
        cutoff_date=cycle.cutoff_date,
        payment_date=cycle.payment_date,
        status=cycle.status.value,
        closed_at=cycle.closed_at,
        capital=amount_or_none(cycle.capital),
        ordinary_interest=amount_or_none(cycle.ordinary_interest),
        late_interest=amount_or_none(cycle.late_interest),
        total=amount_or_none(cycle.total),
    )
