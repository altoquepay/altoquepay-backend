"""Tests for the interest rate formulas, using the figures of the project report."""

from decimal import Decimal

from app.shared.domain.finance import te7d, tep
from app.shared.domain.value_objects import Money, Rate

TEA_75_PERCENT = Decimal("0.75")


def test_te7d_matches_the_report():
    assert Rate(te7d(TEA_75_PERCENT)).percent == Decimal("1.0940836")


def test_tep_capitalizes_the_grace_period_of_the_report():
    capitalized_balance = Decimal("350.00") * (1 + tep(TEA_75_PERCENT, 11))
    assert Money(capitalized_balance).amount == Decimal("356.04")


def test_tep_of_a_full_commercial_year_is_the_annual_rate():
    assert tep(TEA_75_PERCENT, 360) == TEA_75_PERCENT


def test_tep_of_zero_days_is_zero():
    assert tep(TEA_75_PERCENT, 0) == 0
