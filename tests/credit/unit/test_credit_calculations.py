"""The credit calculations against the test data of the report (Pruebas N°1, N°2 and N°3)."""

from datetime import date
from decimal import Decimal

import pytest

from app.credit.domain.services.credit_calculations import (
    capitalize,
    french_schedule,
    interest_over,
)
from app.shared.domain.value_objects import Money, Rate

TEA_75 = Rate.from_percent(Decimal("75"))


def money(value: str) -> Money:
    return Money(Decimal(value))


def rows_of(schedule):
    return [
        (
            row.number,
            row.due_date,
            str(row.opening_balance.amount),
            str(row.interest.amount),
            str(row.amortization.amount),
            str(row.amount.amount),
            str(row.closing_balance.amount),
        )
        for row in schedule
    ]


def test_report_test_1_weekly_purchase_before_the_cutoff():
    principal = capitalize(money("350.00"), TEA_75, days=11)

    schedule = french_schedule(principal, TEA_75, 4, first_period_start=date(2026, 9, 26))

    assert principal == money("356.04")
    assert rows_of(schedule) == [
        (1, date(2026, 10, 3), "356.04", "3.90", "87.56", "91.46", "268.48"),
        (2, date(2026, 10, 10), "268.48", "2.94", "88.52", "91.46", "179.96"),
        (3, date(2026, 10, 17), "179.96", "1.97", "89.49", "91.46", "90.47"),
        (4, date(2026, 10, 24), "90.47", "0.99", "90.47", "91.46", "0.00"),
    ]
    assert sum(row.interest.amount for row in schedule) == Decimal("9.80")
    assert sum(row.amount.amount for row in schedule) == Decimal("365.84")


def test_report_test_3_weekly_purchase_after_the_cutoff():
    principal = capitalize(money("400.00"), TEA_75, days=42)

    schedule = french_schedule(principal, TEA_75, 4, first_period_start=date(2026, 11, 26))

    assert principal == money("426.99")
    assert rows_of(schedule) == [
        (1, date(2026, 12, 3), "426.99", "4.67", "105.01", "109.68", "321.98"),
        (2, date(2026, 12, 10), "321.98", "3.52", "106.16", "109.68", "215.82"),
        (3, date(2026, 12, 17), "215.82", "2.36", "107.32", "109.68", "108.50"),
        (4, date(2026, 12, 24), "108.50", "1.18", "108.50", "109.68", "0.00"),
    ]
    assert sum(row.interest.amount for row in schedule) == Decimal("11.73")
    assert sum(row.amount.amount for row in schedule) == Decimal("438.72")


@pytest.mark.parametrize(
    ("principal", "tea", "count"),
    [("426.99", "75", 4), ("523.45", "40", 6), ("1000.00", "112.5", 8), ("87.31", "20", 1)],
)
def test_every_installment_is_equal_and_every_row_adds_up(principal, tea, count):
    schedule = french_schedule(
        money(principal), Rate.from_percent(Decimal(tea)), count, date(2026, 11, 26)
    )

    assert {row.amount for row in schedule} == {schedule[0].amount}
    for row in schedule:
        assert row.interest.amount + row.amortization.amount == row.amount.amount
        assert row.opening_balance.amount - row.amortization.amount == row.closing_balance.amount
    assert sum(row.amortization.amount for row in schedule) == Decimal(principal)
    assert schedule[-1].closing_balance == money("0")


def test_report_test_2_single_date_purchase_without_interest():
    assert interest_over(money("250.00"), Rate.from_percent(Decimal("0")), days=7) == money("0")


def test_single_date_interest_uses_the_period_rate():
    # 1000 × ((1.75)^(30/360) − 1) = 47.739...
    assert interest_over(money("1000.00"), TEA_75, days=30) == money("47.74")


def test_schedule_without_interest_leaves_the_rounding_cents_to_the_last_installment():
    schedule = french_schedule(
        money("100.00"), Rate.from_percent(Decimal("0")), 3, date(2026, 9, 26)
    )

    assert [str(row.amount.amount) for row in schedule] == ["33.33", "33.33", "33.34"]
    assert schedule[-1].closing_balance == money("0")
