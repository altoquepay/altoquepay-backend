"""The credit calculations: single date interest, weekly total grace and French schedule.

Every amount is rounded to cents as soon as it is produced, so what is stored is what is charged.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.shared.domain.finance import INSTALLMENT_PERIOD_DAYS, te7d, tep
from app.shared.domain.value_objects import Money, Rate


@dataclass(frozen=True)
class ScheduleRow:
    number: int
    due_date: date
    opening_balance: Money
    interest: Money
    amortization: Money
    amount: Money
    closing_balance: Money


def interest_over(amount: Money, tea: Rate, days: int) -> Money:
    """Return the interest of an amount over a number of days, as in a single date purchase."""
    return Money(amount.amount * tep(tea, days))


def capitalize(amount: Money, tea: Rate, days: int) -> Money:
    """Return the debt after a total grace period (Sg): its interest is added to the amount."""
    return Money(amount.amount * (1 + tep(tea, days)))


@dataclass(frozen=True)
class GraceRow:
    """A week of total grace: nothing is paid and its interest is added to the balance."""

    number: int
    end_date: date
    opening_balance: Money
    interest: Money
    closing_balance: Money


def grace_schedule(amount: Money, tea: Rate, weeks: int, start: date) -> list[GraceRow]:
    """Return the weeks of total grace from the purchase day, each adding TE7d of the balance.

    Each interest is rounded to cents, as in the installments, so the rows add up exactly to
    the balance the installments are then calculated on.
    """
    rate = te7d(tea)
    rows = []
    balance = amount.amount
    for number in range(1, weeks + 1):
        interest = Money(balance * rate).amount
        rows.append(
            GraceRow(
                number=number,
                end_date=start + timedelta(days=INSTALLMENT_PERIOD_DAYS * number),
                opening_balance=Money(balance),
                interest=Money(interest),
                closing_balance=Money(balance + interest),
            )
        )
        balance += interest
    return rows


def french_schedule(
    principal: Money, tea: Rate, count: int, first_period_start: date
) -> list[ScheduleRow]:
    """Return the constant weekly installments, the k-th due on first_period_start + 7k days.

    Each interest is rounded to cents and the amortization is the installment minus it. The last
    installment amortizes whatever is left and its interest takes the cents lost to rounding, so
    every installment is equal. Only when that interest is too small to take them, as with no
    interest at all, is the last installment a few cents larger.
    """
    rate = te7d(tea)
    if rate:
        installment = Money(principal.amount * rate / (1 - (1 + rate) ** -count)).amount
    else:
        installment = Money(principal.amount / count).amount
    rows = []
    balance = principal.amount
    for number in range(1, count + 1):
        if number == count:
            amortization = balance
            interest = max(installment - balance, Decimal(0))
        else:
            interest = Money(balance * rate).amount
            amortization = installment - interest
        rows.append(
            ScheduleRow(
                number=number,
                due_date=first_period_start + timedelta(days=INSTALLMENT_PERIOD_DAYS * number),
                opening_balance=Money(balance),
                interest=Money(interest),
                amortization=Money(amortization),
                amount=Money(interest + amortization),
                closing_balance=Money(balance - amortization),
            )
        )
        balance -= amortization
    return rows
