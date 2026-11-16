from decimal import Decimal

from app.billing.domain.model.aggregates.billing_cycle import BillingCycle, CycleStatus
from app.billing.domain.model.aggregates.payment import Payment, PaymentBreakdown, PaymentKind
from app.billing.infrastructure.persistence.models import BillingCycleModel, PaymentModel
from app.shared.domain.value_objects import Money


def money_or_none(amount: Decimal | None) -> Money | None:
    return Money(amount) if amount is not None else None


def amount_or_none(money: Money | None) -> Decimal | None:
    return money.amount if money is not None else None


def to_domain(model: BillingCycleModel) -> BillingCycle:
    return BillingCycle(
        store_customer_id=model.store_customer_id,
        store_id=model.store_id,
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


def copy_to_model(cycle: BillingCycle, model: BillingCycleModel) -> BillingCycleModel:
    model.store_customer_id = cycle.store_customer_id
    model.store_id = cycle.store_id
    model.year = cycle.year
    model.month = cycle.month
    model.cutoff_date = cycle.cutoff_date
    model.payment_date = cycle.payment_date
    model.status = cycle.status.value
    model.closed_at = cycle.closed_at
    model.capital = amount_or_none(cycle.capital)
    model.ordinary_interest = amount_or_none(cycle.ordinary_interest)
    model.late_interest = amount_or_none(cycle.late_interest)
    model.total = amount_or_none(cycle.total)
    return model


def payment_to_domain(model: PaymentModel) -> Payment:
    return Payment(
        store_id=model.store_id,
        account_id=model.store_customer_id,
        kind=PaymentKind(model.kind),
        paid_on=model.paid_on,
        breakdown=PaymentBreakdown(
            late_interest=Money(model.late_interest),
            ordinary_interest=Money(model.ordinary_interest),
            principal=Money(model.principal),
            savings=Money(model.savings),
        ),
        created_by=model.created_by,
        cycle_id=model.billing_cycle_id,
        installment_id=model.installment_id,
        purchase_id=model.purchase_id,
        created_at=model.created_at,
        id=model.id,
    )


def payment_to_model(payment: Payment) -> PaymentModel:
    breakdown = payment.breakdown
    return PaymentModel(
        store_id=payment.store_id,
        store_customer_id=payment.account_id,
        kind=payment.kind.value,
        paid_on=payment.paid_on,
        late_interest=breakdown.late_interest.amount,
        ordinary_interest=breakdown.ordinary_interest.amount,
        principal=breakdown.principal.amount,
        total=breakdown.total.amount,
        savings=breakdown.savings.amount,
        billing_cycle_id=payment.cycle_id,
        installment_id=payment.installment_id,
        purchase_id=payment.purchase_id,
        created_by=payment.created_by,
    )
