"""Tests for assigning a purchase day to its monthly cycle."""

from datetime import date

import pytest

from app.billing.domain.services.cycle_assignment import CyclePeriod, cycle_period_of


@pytest.mark.parametrize(
    ("purchase_day", "cutoff_day", "payment_day", "expected"),
    [
        (date(2026, 9, 15), 20, 26, CyclePeriod(2026, 9, date(2026, 9, 20), date(2026, 9, 26))),
        (date(2026, 9, 20), 20, 26, CyclePeriod(2026, 9, date(2026, 9, 20), date(2026, 9, 26))),
        (date(2026, 9, 21), 20, 26, CyclePeriod(2026, 10, date(2026, 10, 20), date(2026, 10, 26))),
        (date(2026, 10, 15), 14, 26, CyclePeriod(2026, 11, date(2026, 11, 14), date(2026, 11, 26))),
        (date(2026, 12, 20), 14, 26, CyclePeriod(2027, 1, date(2027, 1, 14), date(2027, 1, 26))),
        (date(2027, 1, 30), 25, 28, CyclePeriod(2027, 2, date(2027, 2, 25), date(2027, 2, 28))),
    ],
    ids=["before cutoff", "on cutoff", "after cutoff", "next month", "new year", "february"],
)
def test_purchase_day_falls_in_its_cycle(purchase_day, cutoff_day, payment_day, expected):
    assert cycle_period_of(purchase_day, cutoff_day, payment_day) == expected
