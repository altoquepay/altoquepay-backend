from datetime import date

from app.credit.domain.model.aggregates.purchase import Installment, PaymentMode, Purchase
from app.credit.domain.model.commands.register_purchase_command import (
    RegisterPurchaseCommand,
    RequestedItem,
)
from app.credit.domain.repositories.purchase_repository import InstallmentEntry
from app.credit.interfaces.rest.resources.purchase_resources import (
    GracePeriodResource,
    InstallmentListItemResource,
    InstallmentResource,
    PurchaseDetailResource,
    PurchaseItemResource,
    PurchaseResource,
    RegisterPurchaseResource,
)


def to_register_command(
    resource: RegisterPurchaseResource, store_id: int, user_id: int
) -> RegisterPurchaseCommand:
    return RegisterPurchaseCommand(
        store_id=store_id,
        account_id=resource.customer_id,
        purchased_at=resource.purchased_at,
        mode=resource.mode,
        installments_count=resource.installments_count,
        items=[RequestedItem(item.product_id, item.quantity) for item in resource.items],
        created_by=user_id,
        grace_weeks=resource.grace_weeks,
    )


def to_resource(purchase: Purchase) -> PurchaseResource:
    return PurchaseResource(**purchase_fields(purchase))


def to_detail_resource(purchase: Purchase, today: date) -> PurchaseDetailResource:
    return PurchaseDetailResource(
        **purchase_fields(purchase),
        items=[
            PurchaseItemResource(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_list_price=item.unit_list_price.amount,
                subtotal=item.subtotal.amount,
            )
            for item in purchase.items
        ],
        grace_periods=[
            GracePeriodResource(
                number=row.number,
                end_date=row.end_date,
                opening_balance=row.opening_balance.amount,
                interest=row.interest.amount,
                closing_balance=row.closing_balance.amount,
            )
            for row in purchase.grace_rows()
        ],
        installments=[to_installment_resource(i, today) for i in purchase.installments],
    )


def purchase_fields(purchase: Purchase) -> dict:
    return {
        "id": purchase.id,
        "customer_id": purchase.account_id,
        "cycle_id": purchase.cycle_id,
        "purchased_at": purchase.purchased_at,
        "mode": purchase.mode,
        "amount": purchase.amount.amount,
        "tea": purchase.tea.percent,
        "late_tea": purchase.late_tea.percent,
        "term_days": purchase.term_days,
        "grace_days": purchase.grace_days,
        "grace_weeks": purchase.grace_weeks if purchase.mode == PaymentMode.WEEKLY else None,
        "capitalized_amount": amount_or_none(purchase.capitalized_amount),
        "weekly_rate": None if purchase.weekly_rate is None else purchase.weekly_rate.percent,
        "installments_count": purchase.installments_count,
        "installment_amount": amount_or_none(purchase.installment_amount),
        "ordinary_interest": purchase.ordinary_interest.amount,
        "total": purchase.total.amount,
        "status": purchase.status,
        "voided_at": purchase.voided_at,
        "voided_by": purchase.voided_by,
    }


def amount_or_none(money):
    return None if money is None else money.amount


def to_installment_resource(installment: Installment, today: date) -> InstallmentResource:
    return InstallmentResource(**installment_fields(installment, today))


def to_installment_list_item(entry: InstallmentEntry, today: date) -> InstallmentListItemResource:
    return InstallmentListItemResource(
        **installment_fields(entry.installment, today),
        purchase_id=entry.purchase_id,
        customer_id=entry.account_id,
    )


def installment_fields(installment: Installment, today: date) -> dict:
    return {
        "id": installment.id,
        "number": installment.number,
        "due_date": installment.due_date,
        "opening_balance": installment.opening_balance.amount,
        "interest": installment.interest.amount,
        "amortization": installment.amortization.amount,
        "amount": installment.amount.amount,
        "closing_balance": installment.closing_balance.amount,
        "status": installment.status_on(today),
    }
