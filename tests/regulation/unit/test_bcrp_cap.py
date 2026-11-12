"""Tests for the BcrpCap aggregate."""

from datetime import date
from decimal import Decimal

import pytest

from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Rate

NOVEMBER_2026_CAP = Rate.from_percent(Decimal("114.68"))


def test_late_cap_is_fifteen_percent_of_the_ordinary_cap():
    cap = BcrpCap(NOVEMBER_2026_CAP, date(2026, 11, 1), date(2027, 4, 30))
    assert cap.max_late_tea.percent == Decimal("17.2020000")


def test_validity_period_cannot_end_before_it_starts():
    with pytest.raises(BusinessError) as error:
        BcrpCap(NOVEMBER_2026_CAP, date(2026, 11, 1), date(2026, 10, 31))
    assert error.value.code == "INVALID_VALIDITY_PERIOD"
    assert error.value.field == "valid_to"


def test_cap_must_be_greater_than_zero():
    with pytest.raises(BusinessError) as error:
        BcrpCap(Rate(Decimal("0")), date(2026, 11, 1), date(2027, 4, 30))
    assert error.value.code == "INVALID_RATE"


@pytest.mark.parametrize(
    ("on_date", "covered"),
    [
        (date(2026, 10, 31), False),
        (date(2026, 11, 1), True),
        (date(2027, 4, 30), True),
        (date(2027, 5, 1), False),
    ],
)
def test_validity_period_includes_its_first_and_last_day(on_date, covered):
    cap = BcrpCap(NOVEMBER_2026_CAP, date(2026, 11, 1), date(2027, 4, 30))
    assert cap.covers(on_date) is covered
