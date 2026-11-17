"""Tests for the store account aggregate."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.customers.domain.model.aggregates.store_customer import (
    ACCESS_CODE_LIFETIME,
    AccountStatus,
    StoreCustomer,
)
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import CreditConditions, Money, Rate


def conditions(tea: str) -> CreditConditions:
    return CreditConditions(
        10, 15, Rate.from_percent(Decimal(tea)), Rate.from_percent(Decimal("15")), 4
    )


def test_names_are_trimmed_and_blank_contact_data_is_dropped():
    account = StoreCustomer(
        1,
        2,
        "  Rosa ",
        " Quispe ",
        Money(Decimal("1500")),
        conditions("40"),
        phone="  ",
        address=" Jr. Lima ",
    )

    assert (account.first_names, account.last_names) == ("Rosa", "Quispe")
    assert (account.phone, account.address) == (None, "Jr. Lima")


@pytest.mark.parametrize(
    ("first_names", "last_names", "field"),
    [("  ", "Quispe", "first_names"), ("Rosa", "x" * 101, "last_names")],
)
def test_names_are_required_and_bounded(first_names, last_names, field):
    with pytest.raises(BusinessError) as error:
        StoreCustomer(1, 2, first_names, last_names, Money(Decimal("1500")), conditions("40"))

    assert (error.value.code, error.value.field) == ("INVALID_NAME", field)


def test_contact_update_validates_again():
    account = StoreCustomer(
        1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"), phone="987654321"
    )

    account.update_contact(" Rosa María ", "Quispe", "  ", "Jr. Lima")

    assert account.first_names == "Rosa María"
    assert (account.phone, account.address) == (None, "Jr. Lima")
    with pytest.raises(BusinessError):
        account.update_contact("", "Quispe", None, None)


def test_new_terms_replace_the_old_ones():
    account = StoreCustomer(1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))

    account.update_terms(Money(Decimal("2000")), conditions("75"))

    assert account.credit_limit == Money(Decimal("2000"))
    assert account.conditions.tea.percent == Decimal("75.0000000")


def test_deactivated_account_is_no_longer_active():
    account = StoreCustomer(1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))

    account.deactivate()

    assert (account.status, account.is_active) == (AccountStatus.INACTIVE, False)


NOW = datetime(2026, 11, 17, 10, tzinfo=UTC)


def test_account_starts_out_of_the_portal_and_accepts_its_code_until_it_expires():
    account = StoreCustomer(1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))

    expires_at = account.issue_access_code("hash", NOW)

    assert not account.is_portal_linked
    assert expires_at == NOW + ACCESS_CODE_LIFETIME == NOW + timedelta(hours=48)
    assert account.accepts("hash", NOW)
    assert account.accepts("hash", expires_at - timedelta(seconds=1))
    assert not account.accepts("hash", expires_at)
    assert not account.accepts("another hash", NOW)


def test_a_new_code_replaces_the_previous_one():
    account = StoreCustomer(1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))
    account.issue_access_code("first", NOW)

    account.issue_access_code("second", NOW)

    assert (account.accepts("first", NOW), account.accepts("second", NOW)) == (False, True)


def test_linking_spends_the_code_and_unlinking_hides_the_account_again():
    account = StoreCustomer(1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))
    account.issue_access_code("hash", NOW)

    account.link_portal(NOW)

    assert (account.is_portal_linked, account.accepts("hash", NOW)) == (True, False)
    account.unlink_portal()
    assert not account.is_portal_linked


def test_linking_trusts_the_store_and_unlinking_keeps_the_trust():
    account = StoreCustomer(1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))
    assert not account.portal_trusted

    account.link_portal(NOW)
    account.unlink_portal()

    assert (account.is_portal_linked, account.portal_trusted) == (False, True)


def test_support_trusts_a_store_without_linking_it_and_distrusting_also_unlinks():
    trusted = StoreCustomer(1, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))
    distrusted = StoreCustomer(3, 2, "Rosa", "Quispe", Money(Decimal("1500")), conditions("40"))
    distrusted.link_portal(NOW)

    trusted.trust_portal()
    distrusted.distrust_portal()

    assert (trusted.portal_trusted, trusted.is_portal_linked) == (True, False)
    assert (distrusted.portal_trusted, distrusted.is_portal_linked) == (False, False)
