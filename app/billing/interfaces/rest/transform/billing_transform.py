from datetime import date
from decimal import Decimal

from app.billing.application.command_services.payment_service import PaymentQuote, PaymentTarget
from app.billing.application.query_services.billing_query_service import Statement
from app.billing.domain.model.aggregates.billing_cycle import BillingCycle
from app.billing.domain.model.aggregates.payment import Payment
from app.billing.interfaces.rest.resources.billing_resources import (
    CycleResource,
    PaymentQuoteResource,
    PaymentResource,
    PaymentTargetResource,
    StatementPurchaseResource,
    StatementResource,
)
from app.shared.domain.value_objects import Money


def to_target(resource: PaymentTargetResource) -> PaymentTarget:
    return PaymentTarget(
        kind=resource.kind,
        cycle_id=resource.cycle_id,
        installment_id=resource.installment_id,
        purchase_id=resource.purchase_id,
    )


def to_quote_resource(quote: PaymentQuote) -> PaymentQuoteResource:
    target, breakdown = quote.target, quote.breakdown
    return PaymentQuoteResource(
        kind=target.kind,
        customer_id=quote.account_id,
        paid_on=quote.paid_on,
        cycle_id=target.cycle_id,
        installment_id=target.installment_id,
        purchase_id=target.purchase_id,
        late_interest=breakdown.late_interest.amount,
        ordinary_interest=breakdown.ordinary_interest.amount,
        principal=breakdown.principal.amount,
        total=breakdown.total.amount,
        savings=breakdown.savings.amount,
        days_late=quote.days_late,
        interest_days=quote.interest_days,
    )


def to_payment_resource(payment: Payment) -> PaymentResource:
    if payment.id is None or payment.created_at is None:
        raise ValueError("Only a stored payment has a resource.")
    breakdown = payment.breakdown
    return PaymentResource(
        id=payment.id,
        customer_id=payment.account_id,
        kind=payment.kind,
        paid_on=payment.paid_on,
        cycle_id=payment.cycle_id,
        installment_id=payment.installment_id,
        purchase_id=payment.purchase_id,
        late_interest=breakdown.late_interest.amount,
        ordinary_interest=breakdown.ordinary_interest.amount,
        principal=breakdown.principal.amount,
        total=breakdown.total.amount,
        savings=breakdown.savings.amount,
        created_at=payment.created_at,
    )


def amount_or_none(money: Money | None) -> Decimal | None:
    return money.amount if money is not None else None


def to_cycle_resource(cycle: BillingCycle, today: date) -> CycleResource:
    if cycle.id is None:
        raise ValueError("Only a stored cycle has a resource.")
    return CycleResource(
        id=cycle.id,
        customer_id=cycle.store_customer_id,
        year=cycle.year,
        month=cycle.month,
        cutoff_date=cycle.cutoff_date,
        payment_date=cycle.payment_date,
        status=cycle.status_on(today),
        capital=amount_or_none(cycle.capital),
        ordinary_interest=amount_or_none(cycle.ordinary_interest),
        late_interest=amount_or_none(cycle.late_interest),
        total=amount_or_none(cycle.total),
    )


def to_statement_resource(statement: Statement) -> StatementResource:
    cycle = statement.cycle
    if cycle.id is None:
        raise ValueError("Only a stored cycle has a statement.")
    return StatementResource(
        cycle_id=cycle.id,
        customer_id=cycle.store_customer_id,
        year=cycle.year,
        month=cycle.month,
        cutoff_date=cycle.cutoff_date,
        payment_date=cycle.payment_date,
        status=statement.status,
        capital=statement.totals.capital.amount,
        ordinary_interest=statement.totals.ordinary_interest.amount,
        late_interest=statement.late_interest.amount,
        total=statement.total.amount,
        purchases=[
            StatementPurchaseResource(
                purchase_id=purchase.purchase_id,
                purchased_at=purchase.purchased_at,
                mode=purchase.mode,
                amount=purchase.amount.amount,
                ordinary_interest=purchase.ordinary_interest.amount,
                status=purchase.status,
            )
            for purchase in statement.purchases
        ],
    )
