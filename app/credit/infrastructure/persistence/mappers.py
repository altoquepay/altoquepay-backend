from app.credit.domain.model.aggregates.purchase import (
    Installment,
    InstallmentStatus,
    PaymentMode,
    Purchase,
    PurchaseItem,
    PurchaseStatus,
)
from app.credit.infrastructure.persistence.models import (
    InstallmentModel,
    PurchaseItemModel,
    PurchaseModel,
)
from app.shared.domain.value_objects import Money, Rate


def optional_money(amount) -> Money | None:
    return None if amount is None else Money(amount)


def installment_to_domain(model: InstallmentModel) -> Installment:
    return Installment(
        number=model.number,
        due_date=model.due_date,
        opening_balance=Money(model.opening_balance),
        interest=Money(model.interest),
        amortization=Money(model.amortization),
        amount=Money(model.amount),
        closing_balance=Money(model.closing_balance),
        status=InstallmentStatus(model.status),
        payment_id=model.payment_id,
        id=model.id,
    )


def to_domain(model: PurchaseModel) -> Purchase:
    return Purchase(
        store_id=model.store_id,
        account_id=model.store_customer_id,
        cycle_id=model.billing_cycle_id,
        purchased_at=model.purchased_at,
        mode=PaymentMode(model.mode),
        items=[
            PurchaseItem(item.product_id, item.quantity, Money(item.unit_list_price))
            for item in model.items
        ],
        tea=Rate.from_percent(model.tea),
        late_tea=Rate.from_percent(model.late_tea),
        ordinary_interest=Money(model.ordinary_interest),
        created_by=model.created_by,
        term_days=model.term_days,
        grace_days=model.grace_days,
        capitalized_amount=optional_money(model.capitalized_amount),
        weekly_rate=None if model.weekly_rate is None else Rate.from_percent(model.weekly_rate),
        installments_count=model.installments_count,
        installment_amount=optional_money(model.installment_amount),
        installments=[installment_to_domain(installment) for installment in model.installments],
        status=PurchaseStatus(model.status),
        payment_id=model.payment_id,
        voided_at=model.voided_at,
        voided_by=model.voided_by,
        id=model.id,
    )


def to_model(purchase: Purchase) -> PurchaseModel:
    """Build the rows of a new purchase. Rates are stored as percentages."""
    return PurchaseModel(
        store_id=purchase.store_id,
        store_customer_id=purchase.account_id,
        billing_cycle_id=purchase.cycle_id,
        purchased_at=purchase.purchased_at,
        mode=purchase.mode.value,
        amount=purchase.amount.amount,
        tea=purchase.tea.percent,
        late_tea=purchase.late_tea.percent,
        term_days=purchase.term_days,
        grace_days=purchase.grace_days,
        capitalized_amount=amount_or_none(purchase.capitalized_amount),
        weekly_rate=None if purchase.weekly_rate is None else purchase.weekly_rate.percent,
        installments_count=purchase.installments_count,
        installment_amount=amount_or_none(purchase.installment_amount),
        ordinary_interest=purchase.ordinary_interest.amount,
        status=purchase.status.value,
        created_by=purchase.created_by,
        payment_id=purchase.payment_id,
        items=[
            PurchaseItemModel(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_list_price=item.unit_list_price.amount,
                subtotal=item.subtotal.amount,
            )
            for item in purchase.items
        ],
        installments=[
            InstallmentModel(
                number=installment.number,
                due_date=installment.due_date,
                opening_balance=installment.opening_balance.amount,
                interest=installment.interest.amount,
                amortization=installment.amortization.amount,
                amount=installment.amount.amount,
                closing_balance=installment.closing_balance.amount,
                status=installment.status.value,
                payment_id=installment.payment_id,
            )
            for installment in purchase.installments
        ],
    )


def amount_or_none(money: Money | None):
    return None if money is None else money.amount


def copy_payments_to_model(purchase: Purchase, model: PurchaseModel) -> None:
    """Copy what changes after registration: the statuses, the payments that settled them and
    the voiding."""
    model.status = purchase.status.value
    model.payment_id = purchase.payment_id
    model.voided_at = purchase.voided_at
    model.voided_by = purchase.voided_by
    for installment, installment_model in zip(
        purchase.installments, model.installments, strict=True
    ):
        installment_model.status = installment.status.value
        installment_model.payment_id = installment.payment_id
