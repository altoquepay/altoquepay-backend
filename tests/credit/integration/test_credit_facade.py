"""Tests for the credit facade against the migrated PostgreSQL database. Nothing is committed."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.credit.domain.model.aggregates.purchase import PaymentMode
from app.credit.interfaces.acl.credit_facade import CreditFacade
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork
from tests.credit.stored_credit import (
    LIMA,
    CreditSetup,
    add_credit_setup,
    add_payment,
    add_purchase,
)
from tests.stored_account import add_account, add_customer


@pytest.fixture
async def unit_of_work():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture
async def setup(unit_of_work):
    return await add_credit_setup(unit_of_work)


async def add_single_date(unit_of_work, setup, quantity=1):
    """S/ 100 per unit on 2/11/2026, in the same November cycle as report test N°3."""
    purchased_at = datetime(2026, 11, 2, 9, tzinfo=LIMA)
    return await add_purchase(unit_of_work, setup, purchased_at, PaymentMode.SINGLE_DATE, quantity)


async def test_outstanding_principal_counts_unpaid_amounts_and_installment_principal(
    unit_of_work, setup
):
    facade = CreditFacade(unit_of_work)
    weekly = await add_purchase(unit_of_work, setup)
    await add_single_date(unit_of_work, setup, quantity=2)

    before = await facade.get_outstanding_principal(setup.account_id)
    first_id = weekly.installments[0].id
    payment_id = await add_payment(unit_of_work, setup, installment_id=first_id)
    await facade.mark_installment_paid(first_id, payment_id=payment_id)
    after = await facade.get_outstanding_principal(setup.account_id)

    # 426.99 capitalized plus 200.00, then minus the first amortization of 105.01.
    assert (before, after) == (Decimal("626.99"), Decimal("521.98"))


async def test_installments_and_purchases_are_summarized(unit_of_work, setup):
    facade = CreditFacade(unit_of_work)
    weekly = await add_purchase(unit_of_work, setup)
    single_date = await add_single_date(unit_of_work, setup)

    due = await facade.get_installments_due(setup.account_id, date(2026, 12, 4), date(2026, 12, 17))
    installment = await facade.get_installment(weekly.installments[3].id)
    purchase = await facade.get_purchase(weekly.id)
    cycle_purchases = await facade.get_cycle_purchases(weekly.cycle_id)
    account_purchases = await facade.list_purchases(setup.account_id)

    assert [(i.number, i.amount) for i in due] == [(2, Decimal("109.68")), (3, Decimal("109.68"))]
    assert (installment.number, installment.amount, installment.account_id) == (
        4,
        Decimal("109.69"),
        setup.account_id,
    )
    assert (purchase.mode, purchase.tea, purchase.installment_amount) == (
        "WEEKLY",
        Decimal("75.0000000"),
        Decimal("109.68"),
    )
    assert [p.purchase_id for p in cycle_purchases] == [weekly.id, single_date.id]
    assert [p.purchase_id for p in account_purchases] == [single_date.id, weekly.id]


async def test_paying_the_last_installment_pays_the_purchase(unit_of_work, setup):
    facade = CreditFacade(unit_of_work)
    weekly = await add_purchase(unit_of_work, setup)

    for installment in weekly.installments:
        payment_id = await add_payment(unit_of_work, setup, installment_id=installment.id)
        await facade.mark_installment_paid(installment.id, payment_id=payment_id)

    assert (await facade.get_purchase(weekly.id)).status == "PAID"
    with pytest.raises(BusinessError) as error:
        await facade.mark_installment_paid(weekly.installments[0].id, payment_id=9)
    assert (error.value.code, error.value.status) == ("ALREADY_PAID", 409)


async def test_single_date_purchase_is_paid_and_weekly_one_prepaid(unit_of_work, setup):
    facade = CreditFacade(unit_of_work)
    weekly = await add_purchase(unit_of_work, setup)
    single_date = await add_single_date(unit_of_work, setup)

    single_payment = await add_payment(unit_of_work, setup, purchase_id=single_date.id)
    prepayment = await add_payment(unit_of_work, setup, purchase_id=weekly.id)
    await facade.mark_purchase_paid(single_date.id, payment_id=single_payment)
    await facade.cancel_remaining_installments(weekly.id, payment_id=prepayment)

    assert (await facade.get_purchase(single_date.id)).status == "PAID"
    assert (await facade.get_purchase(weekly.id)).status == "PREPAID"
    assert await facade.get_outstanding_principal(setup.account_id) == Decimal("0.00")
    with pytest.raises(BusinessError) as error:
        await facade.mark_purchase_paid(single_date.id, payment_id=3)
    assert error.value.code == "ALREADY_PAID"


@pytest.mark.parametrize(
    "call",
    [
        lambda facade: facade.get_installment(999999),
        lambda facade: facade.get_purchase(999999),
        lambda facade: facade.mark_installment_paid(999999, 1),
        lambda facade: facade.mark_purchase_paid(999999, 1),
        lambda facade: facade.cancel_remaining_installments(999999, 1),
    ],
)
async def test_unknown_ids_are_not_found(unit_of_work, call):
    with pytest.raises(BusinessError) as error:
        await call(CreditFacade(unit_of_work))

    assert (error.value.code, error.value.status) == ("NOT_FOUND", 404)


async def test_account_without_purchases_has_nothing_outstanding(unit_of_work, setup):
    facade = CreditFacade(unit_of_work)

    assert await facade.get_outstanding_principal(setup.account_id) == Decimal("0")
    assert await facade.list_purchases(setup.account_id) == []


async def test_store_wide_reads_add_up_every_account_of_the_store_only(unit_of_work, setup):
    facade = CreditFacade(unit_of_work)
    neighbor = await add_customer(unit_of_work, dni="70000002")
    second_account = await add_account(unit_of_work, setup.store_id, neighbor.id, 14, 26)
    second = CreditSetup(setup.store_id, second_account.id, setup.product_id, setup.user_id)
    other_store = await add_credit_setup(unit_of_work, ruc="20999999991", dni="70000003")
    weekly = await add_purchase(unit_of_work, setup)
    single_date = await add_single_date(unit_of_work, second, quantity=2)
    await add_single_date(unit_of_work, other_store)

    outstanding = await facade.get_store_outstanding_principal(setup.store_id)
    due = await facade.list_store_installments_due(
        setup.store_id, date(2026, 12, 4), date(2026, 12, 17)
    )
    october_and_november = await facade.list_store_purchases(
        setup.store_id, date(2026, 10, 1), date(2026, 11, 30)
    )
    november = await facade.list_store_purchases(
        setup.store_id, date(2026, 11, 1), date(2026, 11, 30)
    )

    # 426.99 capitalized by the weekly purchase plus 200.00 on a single date.
    assert outstanding == Decimal("626.99")
    assert [(i.number, i.account_id) for i in due] == [
        (2, setup.account_id),
        (3, setup.account_id),
    ]
    assert [p.purchase_id for p in october_and_november] == [single_date.id, weekly.id]
    assert [p.purchase_id for p in november] == [single_date.id]
