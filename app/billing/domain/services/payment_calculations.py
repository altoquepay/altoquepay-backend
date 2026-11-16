"""The report's payment formulas. Every amount is rounded to cents as soon as it is produced."""

from decimal import Decimal

from app.shared.domain.finance import tep
from app.shared.domain.value_objects import Money, Rate

ZERO = Money(Decimal(0))


def interest_for_days(amount: Money, tea: Rate, days: int) -> Money:
    """Return the interest of an amount over some days: amount x ((1 + TEA)^(days/360) - 1)."""
    if days <= 0:
        return ZERO
    return Money(amount.amount * tep(tea, days))


def late_interest(overdue: Money, late_tea: Rate, days_late: int) -> Money:
    """Return the late interest of what should have been paid: overdue x TEPmora(days late).

    Nothing is charged on or before the due date.
    """
    return interest_for_days(overdue, late_tea, days_late)


def savings(owed_interest: Money, charged_interest: Money) -> Money:
    """Return the interest saved by paying early, never negative."""
    return Money(max(owed_interest.amount - charged_interest.amount, Decimal(0)))
