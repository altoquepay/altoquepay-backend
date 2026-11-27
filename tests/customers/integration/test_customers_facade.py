"""Tests for the customers facade against the migrated PostgreSQL database. Nothing is committed."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.customers.domain.model.aggregates.store_customer import AccountStatus
from app.customers.domain.services.access_code import hash_access_code
from app.customers.infrastructure.persistence.store_customer_repository_impl import (
    StoreCustomerRepositoryImpl,
)
from app.customers.interfaces.acl.customers_facade import (
    AccountHolder,
    AccountSummary,
    CreditTerms,
    CustomersFacade,
)
from app.shared.domain.errors import BusinessError
from tests.stored_account import add_account, add_customer
from tests.stored_store import add_store


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
        late_tea=Decimal("90.0000000"),
        cutoff_day=20,
        payment_day=26,
        max_weeks=4,
        status="ACTIVE",
    )


@pytest.mark.parametrize("method", ["get_credit_terms", "lock_account", "get_account_holder"])
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
        AccountSummary(active.id, store.id, "ACTIVE", portal_linked=True),
        AccountSummary(inactive.id, other_store.id, "INACTIVE", portal_linked=True),
    ]
    assert await facade.get_accounts_of_person(999_999) == []


async def test_redeeming_a_code_links_its_store_and_unlinks_the_others(facade, unit_of_work):
    now = datetime.now(UTC)
    store = await add_store(unit_of_work)
    other_store = await add_store(unit_of_work, ruc="20999999991")
    customer = await add_customer(unit_of_work)
    await add_customer(unit_of_work, dni="70000002")
    new_account = await add_account(unit_of_work, store.id, customer.id, portal_linked=False)
    await add_account(unit_of_work, other_store.id, customer.id)
    # Trusted, as an account the customer linked before another store restored their access.
    new_account.trust_portal()
    new_account.issue_access_code(hash_access_code("K7QHM2XWPB"), now)
    await StoreCustomerRepositoryImpl(unit_of_work.session).update(new_account)

    with pytest.raises(BusinessError) as of_another_person:
        await facade.redeem_access_code("70000002", "K7QHM2XWPB", now)
    user_id = await facade.redeem_access_code("70000001", "k7qhm-2xwpb", now)
    with pytest.raises(BusinessError) as already_spent:
        await facade.redeem_access_code("70000001", "K7QHM2XWPB", now)

    assert user_id == customer.user_id
    assert [
        (account.store_id, account.portal_linked)
        for account in await facade.get_accounts_of_person(customer.id)
    ] == [(store.id, True), (other_store.id, False)]
    assert (of_another_person.value.code, already_spent.value.code) == (
        "INVALID_ACCESS_CODE",
        "INVALID_ACCESS_CODE",
    )


async def test_a_store_the_person_does_not_trust_keeps_its_code_unspent(facade, unit_of_work):
    now = datetime.now(UTC)
    store = await add_store(unit_of_work)
    other_store = await add_store(unit_of_work, ruc="20999999991")
    customer = await add_customer(unit_of_work)
    await add_account(unit_of_work, store.id, customer.id)
    untrusted = await add_account(unit_of_work, other_store.id, customer.id, portal_linked=False)
    untrusted.issue_access_code(hash_access_code("K7QHM2XWPB"), now)
    await StoreCustomerRepositoryImpl(unit_of_work.session).update(untrusted)

    with pytest.raises(BusinessError) as error:
        await facade.redeem_access_code("70000001", "K7QHM2XWPB", now)
    # A spent code would now answer INVALID_ACCESS_CODE instead.
    with pytest.raises(BusinessError) as again:
        await facade.redeem_access_code("70000001", "K7QHM2XWPB", now)

    assert (error.value.code, error.value.status) == ("STORE_NOT_TRUSTED", 403)
    assert again.value.code == "STORE_NOT_TRUSTED"
    assert [
        account.portal_linked for account in await facade.get_accounts_of_person(customer.id)
    ] == [True, False]


async def test_customer_of_a_user(facade, unit_of_work):
    customer = await add_customer(unit_of_work)

    assert await facade.get_customer_id_by_user(customer.user_id) == customer.id
    with pytest.raises(BusinessError) as error:
        await facade.get_customer_id_by_user(999_999)
    assert (error.value.code, error.value.status) == ("NOT_FOUND", 404)


async def test_holders_of_a_store_include_inactive_accounts_only_of_it(facade, unit_of_work):
    store = await add_store(unit_of_work)
    other_store = await add_store(unit_of_work, ruc="20999999991")
    rosa = await add_customer(unit_of_work)
    luis = await add_customer(unit_of_work, dni="70000002")
    first = await add_account(unit_of_work, store.id, rosa.id)
    second = await add_account(unit_of_work, store.id, luis.id, status=AccountStatus.INACTIVE)
    await add_account(unit_of_work, other_store.id, rosa.id)

    holders = await facade.list_account_holders(store.id)

    assert holders == [
        AccountHolder(first.id, "ACTIVE", "70000001", "Rosa Quispe Mamani"),
        AccountHolder(second.id, "INACTIVE", "70000002", "Rosa Quispe Mamani"),
    ]
    assert await facade.get_account_holder(first.id) == holders[0]
    assert await facade.list_account_holders(999_999) == []
