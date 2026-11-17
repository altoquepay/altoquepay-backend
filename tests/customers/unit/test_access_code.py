"""Tests for the access code a store hands to a customer."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.customers.domain.model.aggregates.store_customer import StoreCustomer
from app.customers.domain.services.access_code import (
    ACCESS_CODE_ALPHABET,
    ACCESS_CODE_LENGTH,
    generate_access_code,
    hash_access_code,
    redeemed_account,
    restoring_account,
)
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import CreditConditions, Money, Rate

NOW = datetime(2026, 11, 17, 10, tzinfo=UTC)


def account_of_store(store_id: int) -> StoreCustomer:
    rate = Rate.from_percent(Decimal("40"))
    return StoreCustomer(
        store_id, 2, Money(Decimal("1500")), CreditConditions(10, 15, rate, rate, 4)
    )


def test_access_codes_are_random_and_easy_to_dictate():
    codes = {generate_access_code() for _ in range(50)}

    assert len(codes) == 50
    for code in codes:
        assert len(code) == ACCESS_CODE_LENGTH == 12
        assert set(code) <= set(ACCESS_CODE_ALPHABET)
        assert not set(code) & set("0O1I") and code == code.upper()


def test_a_code_typed_in_lowercase_with_spaces_or_hyphens_is_the_same_code():
    assert hash_access_code(" k7qhm-2xwpb ") == hash_access_code("K7QHM2XWPB")
    assert hash_access_code("K7QHM2XWPB") != hash_access_code("K7QHM2XWPC")
    assert "K7QHM2XWPB" not in hash_access_code("K7QHM2XWPB")


def test_a_code_picks_the_account_of_the_store_that_issued_it():
    first, second = account_of_store(1), account_of_store(2)
    first.issue_access_code(hash_access_code("AAAAAAAAAA"), NOW)
    second.issue_access_code(hash_access_code("BBBBBBBBBB"), NOW)

    assert redeemed_account([first, second], "bbbbbbbbbb", NOW) is second


@pytest.mark.parametrize("code", ["CCCCCCCCCC", ""])
def test_a_code_of_no_account_is_refused(code):
    account = account_of_store(1)
    account.issue_access_code(hash_access_code("AAAAAAAAAA"), NOW)

    with pytest.raises(BusinessError) as error:
        redeemed_account([account, account_of_store(2)], code, NOW)

    assert (error.value.code, error.value.field, error.value.status) == (
        "INVALID_ACCESS_CODE",
        "code",
        422,
    )


def accounts_with_code_at_second(*, first_trusted: bool, second_trusted: bool) -> list:
    first, second = account_of_store(1), account_of_store(2)
    first.portal_trusted, second.portal_trusted = first_trusted, second_trusted
    second.issue_access_code(hash_access_code("BBBBBBBBBB"), NOW)
    return [first, second]


@pytest.mark.parametrize(
    ("first_trusted", "second_trusted"),
    [(False, False), (True, True), (False, True)],
    ids=["first activation", "trusted store", "only the store of the code is trusted"],
)
def test_a_code_restores_the_access_when_its_store_is_trusted_or_nobody_is(
    first_trusted, second_trusted
):
    accounts = accounts_with_code_at_second(
        first_trusted=first_trusted, second_trusted=second_trusted
    )

    assert restoring_account(accounts, "BBBBBBBBBB", NOW) is accounts[1]


def test_a_store_the_person_does_not_trust_cannot_restore_their_access():
    accounts = accounts_with_code_at_second(first_trusted=True, second_trusted=False)

    with pytest.raises(BusinessError) as error:
        restoring_account(accounts, "BBBBBBBBBB", NOW)

    assert (error.value.code, error.value.field, error.value.status) == (
        "STORE_NOT_TRUSTED",
        "code",
        403,
    )
    assert accounts[1].accepts(hash_access_code("BBBBBBBBBB"), NOW)
