"""Tests for the shared value objects."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni, Money, Rate, Ruc


def test_money_rounds_half_up_to_two_decimals():
    assert Money(Decimal("356.045")).amount == Decimal("356.05")
    assert Money(Decimal("0")).amount == Decimal("0.00")


@pytest.mark.parametrize(
    "invalid_amount",
    [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("1E+10"), 350.0, "350"],
)
def test_money_rejects_invalid_amounts(invalid_amount):
    with pytest.raises(BusinessError) as error:
        Money(invalid_amount)
    assert error.value.code == "INVALID_AMOUNT"
    assert error.value.field == "amount"


def test_value_objects_are_immutable():
    with pytest.raises(FrozenInstanceError):
        Money(Decimal("1")).amount = Decimal("2")


def test_rate_converts_between_percent_and_fraction():
    rate = Rate.from_percent(Decimal("75"))
    assert rate.fraction == Decimal("0.75")
    assert rate.percent == Decimal("75.0000000")


def test_rate_rounds_percent_to_seven_decimals_but_keeps_full_precision():
    rate = Rate(Decimal("0.0109408360502"))
    assert rate.percent == Decimal("1.0940836")
    assert rate.fraction == Decimal("0.0109408360502")


@pytest.mark.parametrize(
    "invalid_fraction", [Decimal("-0.1"), Decimal("NaN"), Decimal("1000"), 0.75]
)
def test_rate_rejects_invalid_fractions(invalid_fraction):
    with pytest.raises(BusinessError) as error:
        Rate(invalid_fraction)
    assert error.value.code == "INVALID_RATE"


def test_dni_keeps_leading_zeros():
    assert Dni("01234567").value == "01234567"


@pytest.mark.parametrize("invalid_dni", ["", "1234567", "123456789", "1234567a", "١٢٣٤٥٦٧٨"])
def test_dni_requires_eight_ascii_digits(invalid_dni):
    with pytest.raises(BusinessError) as error:
        Dni(invalid_dni)
    assert error.value.code == "INVALID_DNI"


def test_ruc_keeps_all_digits():
    assert Ruc("20123456789").value == "20123456789"


@pytest.mark.parametrize("invalid_ruc", ["", "2012345678", "201234567890", "2012345678a"])
def test_ruc_requires_eleven_digits(invalid_ruc):
    with pytest.raises(BusinessError) as error:
        Ruc(invalid_ruc)
    assert error.value.code == "INVALID_RUC"
