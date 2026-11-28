"""The credit calculations: single date interest, weekly total grace and French schedule.

Every amount is rounded to cents as soon as it is produced, so what is stored is what is charged.
"""

from collections.abc import Collection
from dataclasses import dataclass, replace
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
    """A week of total grace: nothing is paid and its interest is added to the balance.

    number counts the grace weeks; week is its place in the plan, counted from the purchase.
    """

    number: int
    week: int
    end_date: date
    opening_balance: Money
    interest: Money
    closing_balance: Money


def weekly_plan(
    amount: Money, tea: Rate, installments_count: int, grace_weeks: Collection[int], start: date
) -> tuple[list[GraceRow], list[ScheduleRow]]:
    """Return the grace weeks and the installments of a weekly plan, week k ending on start + 7k.

    The plan lasts installments_count plus the grace weeks, and any week but the last may be of
    grace: nothing is paid and its interest, rounded to cents, is added to the balance. Each run
    of installments is a French schedule of the balance over the installments still to pay, so
    after a grace week the installments go up; without grace it is one French schedule.
    """
    grace = set(grace_weeks)
    weeks = installments_count + len(grace)
    rate = te7d(tea)
    balance = amount.amount
    grace_rows: list[GraceRow] = []
    rows: list[ScheduleRow] = []
    week = 1
    while week <= weeks:
        if week in grace:
            interest = Money(balance * rate).amount
            grace_rows.append(
                GraceRow(
                    number=len(grace_rows) + 1,
                    week=week,
                    end_date=start + timedelta(days=INSTALLMENT_PERIOD_DAYS * week),
                    opening_balance=Money(balance),
                    interest=Money(interest),
                    closing_balance=Money(balance + interest),
                )
            )
            balance += interest
            week += 1
            continue
        run_end = min((w for w in grace if w > week), default=weeks + 1)
        run_start = start + timedelta(days=INSTALLMENT_PERIOD_DAYS * (week - 1))
        remaining = installments_count - len(rows)
        run = french_schedule(Money(balance), tea, remaining, run_start)[: run_end - week]
        paid_before = len(rows)
        rows.extend(replace(row, number=paid_before + row.number) for row in run)
        balance = run[-1].closing_balance.amount
        week = run_end
    return grace_rows, rows


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
