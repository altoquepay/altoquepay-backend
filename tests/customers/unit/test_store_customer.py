"""Tests for the store account aggregate."""

from decimal import Decimal

from app.customers.domain.model.aggregates.store_customer import AccountStatus, StoreCustomer
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
