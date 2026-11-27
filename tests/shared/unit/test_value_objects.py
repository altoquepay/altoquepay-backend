"""Tests for the shared value objects."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import (
    CreditConditions,
    Dni,
    Money,
    Rate,
    Ruc,
    optional_phone,
)


def test_money_rounds_half_up_to_two_decimals():
    assert Money(Decimal("356.045")).amount == Decimal("356.05")
    assert Money(Decimal("0")).amount == Decimal("0.00")


def test_money_turns_negative_zero_into_zero():
    # Decimal("-0.00") equals Decimal("0.00"), so only the text shows the sign.
    assert str(Money(Decimal("-0")).amount) == "0.00"


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
    "invalid_fraction",
    [Decimal("-0.1"), Decimal("NaN"), Decimal("1000"), Decimal("9E+999999"), 0.75],
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


@pytest.mark.parametrize(
    ("typed", "kept"),
    [
        ("987654321", "987654321"),
        (" +51 987 654 321 ", "+51 987 654 321"),
        ("01 234-5678", "01 234-5678"),
        ("  ", None),
        (None, None),
    ],
)
def test_phone_is_kept_as_typed_and_blank_means_none(typed, kept):
    assert optional_phone(typed) == kept


@pytest.mark.parametrize(
    "invalid_phone",
    ["abcdefgh", "98765", "987--654", "(01) 2345678", "9876543210123456", "+51 98765432a"],
)
def test_phone_needs_six_to_fifteen_digits(invalid_phone):
    with pytest.raises(BusinessError) as error:
        optional_phone(invalid_phone)
    assert (error.value.code, error.value.field) == ("INVALID_PHONE", "phone")


def credit_conditions(**overrides) -> CreditConditions:
    values = {
        "cutoff_day": 10,
        "payment_day": 15,
        "tea": Rate.from_percent(Decimal("40")),
        "late_tea": Rate.from_percent(Decimal("15")),
        "max_weeks": 4,
    } | overrides
    return CreditConditions(**values)


def test_credit_conditions_accept_the_edges_of_each_range():
    assert credit_conditions(cutoff_day=1, payment_day=2, max_weeks=1).cutoff_day == 1
    assert credit_conditions(cutoff_day=25, payment_day=28, max_weeks=99).payment_day == 28


@pytest.mark.parametrize(
    ("invalid_values", "code", "field"),
    [
        ({"cutoff_day": 0}, "INVALID_DAY_RANGE", "cutoff_day"),
        ({"cutoff_day": 26, "payment_day": 28}, "INVALID_DAY_RANGE", "cutoff_day"),
        ({"payment_day": 0}, "INVALID_DAY_RANGE", "payment_day"),
        ({"payment_day": 29}, "INVALID_DAY_RANGE", "payment_day"),
        ({"payment_day": 10}, "PAYMENT_DAY_NOT_AFTER_CUTOFF", "payment_day"),
        ({"max_weeks": 0}, "INVALID_MAX_WEEKS", "max_weeks"),
        ({"max_weeks": 100}, "INVALID_MAX_WEEKS", "max_weeks"),
    ],
)
def test_credit_conditions_reject_values_out_of_range(invalid_values, code, field):
    with pytest.raises(BusinessError) as error:
        credit_conditions(**invalid_values)
    assert (error.value.code, error.value.field) == (code, field)


@pytest.mark.parametrize(("tea", "late_tea"), [("40", "40"), ("75", "10")])
def test_late_rate_must_be_above_the_tea_when_saved(tea, late_tea):
    conditions = credit_conditions(
        tea=Rate.from_percent(Decimal(tea)), late_tea=Rate.from_percent(Decimal(late_tea))
    )

    with pytest.raises(BusinessError) as error:
        conditions.ensure_late_above_ordinary()

    assert (error.value.code, error.value.field) == ("LATE_TEA_NOT_ABOVE_TEA", "late_tea")


def test_late_rate_above_the_tea_has_no_upper_limit():
    credit_conditions(
        tea=Rate.from_percent(Decimal("40")), late_tea=Rate.from_percent(Decimal("150"))
    ).ensure_late_above_ordinary()
