"""Tests for the Purchase aggregate."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.credit.domain.model.aggregates.purchase import (
    InstallmentStatus,
    PaymentMode,
    Purchase,
    PurchaseItem,
    PurchaseStatus,
)
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money, Rate


def register(mode=PaymentMode.WEEKLY, installments_count=4, max_weeks=8, items=None):
    """Report test N°3: S/ 400 bought on 15/10/2026, paid from the cycle of 26/11/2026."""
    purchase = Purchase.register(
        store_id=1,
        account_id=2,
        cycle_id=3,
        cycle_payment_date=date(2026, 11, 26),
        purchased_at=datetime(2026, 10, 15, 17, tzinfo=UTC),
        purchase_day=date(2026, 10, 15),
        mode=mode,
        items=[PurchaseItem(10, 4, Money(Decimal("100.00")))] if items is None else items,
        tea=Rate.from_percent(Decimal("75")),
        late_tea=Rate.from_percent(Decimal("8.5")),
        installments_count=installments_count,
        max_weeks=max_weeks,
        created_by=7,
    )
    for number, installment in enumerate(purchase.installments, start=1):
        installment.id = 100 + number
    return purchase


def test_weekly_purchase_has_the_report_schedule():
    purchase = register()

    assert purchase.amount == Money(Decimal("400"))
    assert (purchase.grace_days, purchase.term_days) == (42, None)
    assert purchase.capitalized_amount == Money(Decimal("426.99"))
    assert purchase.weekly_rate.percent.quantize(Decimal("0.0000001")) == Decimal("1.0940836")
    assert purchase.installment_amount == Money(Decimal("109.68"))
    assert purchase.ordinary_interest == Money(Decimal("11.74"))
    assert [i.amount.amount for i in purchase.installments][-1] == Decimal("109.69")


def test_single_date_purchase_charges_the_interest_until_the_cycle_payment_date():
    purchase = register(mode=PaymentMode.SINGLE_DATE, installments_count=None)

    assert (purchase.term_days, purchase.installments) == (42, [])
    # 400 × ((1.75)^(42/360) − 1) = 26.986...
    assert purchase.ordinary_interest == Money(Decimal("26.99"))
    assert purchase.outstanding_principal() == Money(Decimal("400"))


@pytest.mark.parametrize(
    ("mode", "count", "code"),
    [
        (PaymentMode.WEEKLY, None, "INVALID_INSTALLMENTS_COUNT"),
        (PaymentMode.WEEKLY, 0, "INVALID_INSTALLMENTS_COUNT"),
        (PaymentMode.WEEKLY, 9, "MAX_WEEKS_EXCEEDED"),
        (PaymentMode.SINGLE_DATE, 2, "INVALID_INSTALLMENTS_COUNT"),
    ],
)
def test_installments_count_must_fit_the_mode_and_the_maximum_weeks(mode, count, code):
    with pytest.raises(BusinessError) as error:
        register(mode=mode, installments_count=count)

    assert (error.value.code, error.value.field) == (code, "installments_count")


def test_items_need_a_quantity_and_the_purchase_needs_items():
    with pytest.raises(BusinessError) as no_quantity:
        PurchaseItem(10, 0, Money(Decimal("1")))
    with pytest.raises(BusinessError) as no_items:
        register(items=[])

    assert no_quantity.value.code == "INVALID_QUANTITY"
    assert no_items.value.code == "NO_ITEMS"


def test_paying_every_installment_pays_the_purchase():
    purchase = register(installments_count=2)

    purchase.mark_installment_paid(101, payment_id=50)
    assert purchase.status == PurchaseStatus.ACTIVE
    assert purchase.outstanding_principal() == purchase.installments[1].amortization
    purchase.mark_installment_paid(102, payment_id=51)

    assert purchase.status == PurchaseStatus.PAID
    assert purchase.outstanding_principal() == Money(Decimal(0))
    with pytest.raises(BusinessError) as error:
        purchase.mark_installment_paid(101, payment_id=52)
    assert (error.value.code, error.value.status) == ("ALREADY_PAID", 409)


def test_prepaying_cancels_only_the_pending_installments():
    purchase = register()
    purchase.mark_installment_paid(101, payment_id=50)

    purchase.cancel_remaining_installments(payment_id=60)

    assert purchase.status == PurchaseStatus.PREPAID
    assert [i.status for i in purchase.installments] == [InstallmentStatus.PAID] + [
        InstallmentStatus.CANCELLED
    ] * 3
    assert purchase.installments[0].payment_id == 50
    with pytest.raises(BusinessError) as error:
        purchase.cancel_remaining_installments(payment_id=61)
    assert error.value.code == "ALREADY_PAID"


def test_single_date_purchase_is_paid_once():
    purchase = register(mode=PaymentMode.SINGLE_DATE, installments_count=None)

    purchase.mark_paid(payment_id=70)

    assert (purchase.status, purchase.payment_id) == (PurchaseStatus.PAID, 70)
    with pytest.raises(BusinessError) as error:
        purchase.mark_paid(payment_id=71)
    assert error.value.code == "ALREADY_PAID"


def test_pending_installment_past_its_due_date_shows_as_overdue():
    installment = register().installments[0]  # due on 03/12/2026

    assert installment.status_on(date(2026, 12, 3)) == InstallmentStatus.PENDING
    assert installment.status_on(date(2026, 12, 4)) == InstallmentStatus.OVERDUE


def test_a_product_goes_in_one_item_only():
    price = Money(Decimal("1"))

    with pytest.raises(BusinessError) as error:
        register(items=[PurchaseItem(10, 1, price), PurchaseItem(10, 2, price)])

    assert (error.value.code, error.value.field) == ("DUPLICATE_PRODUCT", "items")


def test_total_is_what_the_customer_pays():
    weekly = register()
    single_date = register(mode=PaymentMode.SINGLE_DATE, installments_count=None)

    assert weekly.total == Money(Decimal("438.73"))
    assert single_date.total == Money(Decimal("426.99"))
