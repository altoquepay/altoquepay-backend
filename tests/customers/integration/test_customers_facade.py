"""Tests for the customers facade against the migrated PostgreSQL database. Nothing is committed."""

from decimal import Decimal

import pytest

from app.customers.domain.model.aggregates.store_customer import AccountStatus
from app.customers.interfaces.acl.customers_facade import (
    AccountSummary,
    CreditTerms,
    CustomersFacade,
)
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork
from tests.stored_account import add_account, add_customer
from tests.stored_store import add_store


@pytest.fixture
async def unit_of_work():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture
def facade(unit_of_work):
    return CustomersFacade(unit_of_work)


async def test_credit_terms_have_rates_in_percent(facade, unit_of_work):
    store = await add_store(unit_of_work)
    customer = await add_customer(unit_of_work)
    account = await add_account(unit_of_work, store.id, customer.id)

    terms = await facade.get_credit_terms(account.id)

    assert terms == CreditTerms(
        account_id=account.id,
        store_id=store.id,
        customer_id=customer.id,
        credit_limit=Decimal("1500.00"),
        tea=Decimal("75.0000000"),
        late_tea=Decimal("10.0000000"),
        cutoff_day=20,
        payment_day=26,
        max_weeks=4,
        status="ACTIVE",
    )


@pytest.mark.parametrize("method", ["get_credit_terms", "lock_account"])
async def test_unknown_account_is_not_found(facade, method):
    with pytest.raises(BusinessError) as error:
        await getattr(facade, method)(999_999)

    assert (error.value.code, error.value.status) == ("NOT_FOUND", 404)


async def test_existing_account_can_be_locked(facade, unit_of_work):
    store = await add_store(unit_of_work)
    customer = await add_customer(unit_of_work)
    account = await add_account(unit_of_work, store.id, customer.id)

    await facade.lock_account(account.id)


async def test_count_skips_inactive_accounts_and_other_stores(facade, unit_of_work):
    store = await add_store(unit_of_work)
    other_store = await add_store(unit_of_work, ruc="20999999991")
    for number, (store_id, status) in enumerate(
        [
            (store.id, AccountStatus.ACTIVE),
            (store.id, AccountStatus.ACTIVE),
            (store.id, AccountStatus.INACTIVE),
            (other_store.id, AccountStatus.ACTIVE),
        ]
    ):
        customer = await add_customer(unit_of_work, dni=f"7000000{number}")
        await add_account(unit_of_work, store_id, customer.id, status=status)

    assert await facade.count_by_store(store.id) == 2
    assert await facade.count_by_store(999_999) == 0


async def test_accounts_of_a_person_include_inactive_ones(facade, unit_of_work):
    store = await add_store(unit_of_work)
    other_store = await add_store(unit_of_work, ruc="20999999991")
    customer = await add_customer(unit_of_work)
    active = await add_account(unit_of_work, store.id, customer.id)
    inactive = await add_account(
        unit_of_work, other_store.id, customer.id, status=AccountStatus.INACTIVE
    )

    accounts = await facade.get_accounts_of_person(customer.id)

    assert accounts == [
        AccountSummary(active.id, store.id, "ACTIVE"),
        AccountSummary(inactive.id, other_store.id, "INACTIVE"),
    ]
    assert await facade.get_accounts_of_person(999_999) == []


async def test_customer_of_a_user(facade, unit_of_work):
    customer = await add_customer(unit_of_work)

    assert await facade.get_customer_id_by_user(customer.user_id) == customer.id
    with pytest.raises(BusinessError) as error:
        await facade.get_customer_id_by_user(999_999)
    assert (error.value.code, error.value.status) == ("NOT_FOUND", 404)


async def test_accounts_of_a_store_include_inactive_ones_and_no_other_store(facade, unit_of_work):
    store = await add_store(unit_of_work)
    other_store = await add_store(unit_of_work, ruc="20999999991")
    rosa = await add_customer(unit_of_work)
    luis = await add_customer(unit_of_work, dni="70000002")
    first = await add_account(unit_of_work, store.id, rosa.id)
    second = await add_account(unit_of_work, store.id, luis.id, status=AccountStatus.INACTIVE)
    await add_account(unit_of_work, other_store.id, rosa.id)

    accounts = await facade.list_accounts_of_store(store.id)

    assert accounts == [
        AccountSummary(first.id, store.id, "ACTIVE"),
        AccountSummary(second.id, store.id, "INACTIVE"),
    ]
    assert await facade.list_accounts_of_store(999_999) == []
