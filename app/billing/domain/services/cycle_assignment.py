"""Which monthly cycle a purchase belongs to, from its day in the business time zone."""

from dataclasses import dataclass
from datetime import date

DECEMBER = 12


@dataclass(frozen=True)
class CyclePeriod:
    year: int
    month: int
    cutoff_date: date
    payment_date: date


def cycle_period_of(purchase_day: date, cutoff_day: int, payment_day: int) -> CyclePeriod:
    """A purchase up to the end of the cutoff day falls in that month; later ones in the next.

    Cutoff and payment days stop at 25 and 28, so both dates exist in every month.
    """
    year, month = purchase_day.year, purchase_day.month
    if purchase_day.day > cutoff_day:
        year, month = (year + 1, 1) if month == DECEMBER else (year, month + 1)
    return CyclePeriod(
        year=year,
        month=month,
        cutoff_date=date(year, month, cutoff_day),
        payment_date=date(year, month, payment_day),
    )
