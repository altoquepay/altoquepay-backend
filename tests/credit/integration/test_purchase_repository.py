"""Tests for the purchase repository against the migrated PostgreSQL database. Nothing commits."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.credit.domain.model.aggregates.purchase import (
    InstallmentStatus,
    PaymentMode,
    PurchaseStatus,
)
from app.credit.domain.repositories.purchase_repository import PurchaseFilter
from app.credit.infrastructure.persistence.purchase_repository_impl import PurchaseRepositoryImpl
from app.shared.domain.value_objects import Money
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork
from tests.credit.stored_credit import (
    DUE_DATES_OF_TEST_3,
    LIMA,
    add_credit_setup,
    add_purchase,
)


@pytest.fixture
async def unit_of_work():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


async def test_stored_purchase_reads_back_equal(unit_of_work):
    setup = await add_credit_setup(unit_of_work)
    purchase = await add_purchase(unit_of_work, setup)
    unit_of_work.session.expunge_all()

    stored = await PurchaseRepositoryImpl(unit_of_work.session).find_by_id(purchase.id)

    assert stored == purchase
    assert [installment.due_date for installment in stored.installments] == DUE_DATES_OF_TEST_3
    assert stored.amount == Money(Decimal("400"))


async def test_paying_installments_is_saved(unit_of_work):
    repository = PurchaseRepositoryImpl(unit_of_work.session)
    setup = await add_credit_setup(unit_of_work)
    purchase = await add_purchase(unit_of_work, setup)
    first, second = purchase.installments[0].id, purchase.installments[1].id

    purchase.mark_installment_paid(first, payment_id=900)
    purchase.cancel_remaining_installments(payment_id=901)
    await repository.update(purchase)
    unit_of_work.session.expunge_all()
    stored = await repository.find_by_installment(second)

    assert stored.status == PurchaseStatus.PREPAID
    assert [(i.status, i.payment_id) for i in stored.installments][:2] == [
        (InstallmentStatus.PAID, 900),
        (InstallmentStatus.CANCELLED, 901),
    ]
    assert await repository.list_active_by_account(setup.account_id) == []


async def test_purchases_are_listed_by_store_with_filters(unit_of_work):
    repository = PurchaseRepositoryImpl(unit_of_work.session)
    setup = await add_credit_setup(unit_of_work)
    other_store = await add_credit_setup(unit_of_work, ruc="20999999991", dni="70000002")
    october = await add_purchase(unit_of_work, setup)
    # 23:30 in Lima on 31/10 is already 1/11 in UTC, but it is still an October purchase.
    late_october = await add_purchase(
        unit_of_work, setup, datetime(2026, 10, 31, 23, 30, tzinfo=LIMA), PaymentMode.SINGLE_DATE, 1
    )
    await add_purchase(unit_of_work, other_store)

    everything, total = await repository.list_page(setup.store_id, PurchaseFilter(), 0, 10)
    single_date, _ = await repository.list_page(
        setup.store_id, PurchaseFilter(mode=PaymentMode.SINGLE_DATE), 0, 10
    )
    in_october, _ = await repository.list_page(
        setup.store_id,
        PurchaseFilter(from_date=date(2026, 10, 1), to_date=date(2026, 10, 31)),
        0,
        10,
    )
    from_november, _ = await repository.list_page(
        setup.store_id, PurchaseFilter(from_date=date(2026, 11, 1)), 0, 10
    )

    assert ([p.id for p in everything], total) == ([late_october.id, october.id], 2)
    assert [p.id for p in single_date] == [late_october.id]
    assert len(in_october) == 2
    assert from_november == []
    # Both are after the cutoff of the 14th, so both belong to the November cycle.
    cycle_purchases = await repository.list_by_cycle(october.cycle_id)
    assert [p.id for p in cycle_purchases] == [october.id, late_october.id]


async def test_installments_are_listed_with_their_status_today(unit_of_work):
    repository = PurchaseRepositoryImpl(unit_of_work.session)
    setup = await add_credit_setup(unit_of_work)
    purchase = await add_purchase(unit_of_work, setup)
    today = date(2026, 12, 11)  # the first two installments are past due

    overdue, overdue_total = await repository.list_installments(
        setup.store_id, InstallmentStatus.OVERDUE, None, today, 0, 10
    )
    pending, _ = await repository.list_installments(
        setup.store_id, InstallmentStatus.PENDING, None, today, 0, 10
    )
    due_by_the_17th, _ = await repository.list_installments(
        setup.store_id, None, date(2026, 12, 17), today, 0, 10
    )
    due_in_range = await repository.list_installments_due(
        setup.account_id, date(2026, 12, 10), date(2026, 12, 17)
    )
    entry = await repository.find_installment(purchase.installments[3].id)

    assert ([e.installment.number for e in overdue], overdue_total) == ([1, 2], 2)
    assert [e.installment.number for e in pending] == [3, 4]
    assert [e.installment.number for e in due_by_the_17th] == [1, 2, 3]
    assert [e.installment.number for e in due_in_range] == [2, 3]
    assert (entry.purchase_id, entry.account_id, entry.installment.number) == (
        purchase.id,
        setup.account_id,
        4,
    )
