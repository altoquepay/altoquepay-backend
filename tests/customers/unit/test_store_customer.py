"""Tests for the store account aggregate."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.customers.domain.model.aggregates.store_customer import (
    ACCESS_CODE_LIFETIME,
    AccountStatus,
    StoreCustomer,
)
from app.shared.domain.value_objects import CreditConditions, Money, Rate


def conditions(tea: str) -> CreditConditions:
    return CreditConditions(
        10, 15, Rate.from_percent(Decimal(tea)), Rate.from_percent(Decimal("15")), 4
    )


def test_new_terms_replace_the_old_ones():
    account = StoreCustomer(1, 2, Money(Decimal("1500")), conditions("40"))

    account.update_terms(Money(Decimal("2000")), conditions("75"))

    assert account.credit_limit == Money(Decimal("2000"))
    assert account.conditions.tea.percent == Decimal("75.0000000")


def test_deactivated_account_is_no_longer_active():
    account = StoreCustomer(1, 2, Money(Decimal("1500")), conditions("40"))

    account.deactivate()

    assert (account.status, account.is_active) == (AccountStatus.INACTIVE, False)


NOW = datetime(2026, 11, 17, 10, tzinfo=UTC)


def test_account_starts_out_of_the_portal_and_accepts_its_code_until_it_expires():
    account = StoreCustomer(1, 2, Money(Decimal("1500")), conditions("40"))

    expires_at = account.issue_access_code("hash", NOW)

    assert not account.is_portal_linked
    assert expires_at == NOW + ACCESS_CODE_LIFETIME == NOW + timedelta(hours=48)
    assert account.accepts("hash", NOW)
    assert account.accepts("hash", expires_at - timedelta(seconds=1))
    assert not account.accepts("hash", expires_at)
    assert not account.accepts("another hash", NOW)


def test_a_new_code_replaces_the_previous_one():
    account = StoreCustomer(1, 2, Money(Decimal("1500")), conditions("40"))
    account.issue_access_code("first", NOW)

    account.issue_access_code("second", NOW)

    assert (account.accepts("first", NOW), account.accepts("second", NOW)) == (False, True)


def test_linking_spends_the_code_and_unlinking_hides_the_account_again():
    account = StoreCustomer(1, 2, Money(Decimal("1500")), conditions("40"))
    account.issue_access_code("hash", NOW)

    account.link_portal(NOW)

    assert (account.is_portal_linked, account.accepts("hash", NOW)) == (True, False)
    account.unlink_portal()
    assert not account.is_portal_linked


def test_linking_trusts_the_store_and_unlinking_keeps_the_trust():
    account = StoreCustomer(1, 2, Money(Decimal("1500")), conditions("40"))
    assert not account.portal_trusted

    account.link_portal(NOW)
    account.unlink_portal()

    assert (account.is_portal_linked, account.portal_trusted) == (False, True)


def test_support_trusts_a_store_without_linking_it_and_distrusting_also_unlinks():
    trusted = StoreCustomer(1, 2, Money(Decimal("1500")), conditions("40"))
    distrusted = StoreCustomer(3, 2, Money(Decimal("1500")), conditions("40"))
    distrusted.link_portal(NOW)

    trusted.trust_portal()
    distrusted.distrust_portal()

    assert (trusted.portal_trusted, trusted.is_portal_linked) == (True, False)
    assert (distrusted.portal_trusted, distrusted.is_portal_linked) == (False, False)
