"""Interest rate formulas on a 360-day commercial year. Results keep full precision."""

from decimal import Decimal

from app.shared.domain.value_objects import Rate

COMMERCIAL_YEAR_DAYS = 360
INSTALLMENT_PERIOD_DAYS = 7


def tep(tea: Rate, days: int) -> Decimal:
    """Return the effective rate of a period of days (TEP) from an annual effective rate (TEA)."""
    return (1 + tea.fraction) ** (Decimal(days) / COMMERCIAL_YEAR_DAYS) - 1


def te7d(tea: Rate) -> Decimal:
    """Return the effective rate of a weekly installment period (TE7d)."""
    return tep(tea, INSTALLMENT_PERIOD_DAYS)
