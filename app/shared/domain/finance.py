"""Interest rate formulas on a 360-day commercial year. Rates have 7 decimals as a percentage."""

from decimal import ROUND_HALF_UP, Decimal

from app.shared.domain.value_objects import RATE_PERCENT_STEP, Rate

COMMERCIAL_YEAR_DAYS = 360
INSTALLMENT_PERIOD_DAYS = 7


def tep(tea: Rate, days: int) -> Decimal:
    """Return the effective rate of a period of days (TEP) from an annual effective rate (TEA)."""
    rate = (1 + tea.fraction) ** (Decimal(days) / COMMERCIAL_YEAR_DAYS) - 1
    return (rate * 100).quantize(RATE_PERCENT_STEP, ROUND_HALF_UP) / 100


def te7d(tea: Rate) -> Decimal:
    """Return the effective rate of a weekly installment period (TE7d)."""
    return tep(tea, INSTALLMENT_PERIOD_DAYS)
