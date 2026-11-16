"""Tests for how payments are applied and calculated, and how cycles close."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.billing.domain.model.aggregates.billing_cycle import (
    BillingCycle,
    CycleStatus,
    StatementTotals,
)
from app.billing.domain.model.aggregates.payment import PaymentBreakdown
from app.billing.domain.services.cycle_assignment import cycle_period_of
from app.billing.domain.services.payment_calculations import (
    interest_for_days,
    late_interest,
    savings,
)
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money, Rate


def money(amount: str) -> Money:
    return Money(Decimal(amount))


DUE = PaymentBreakdown(money("0.09"), money("4.67"), money("105.01"))


def test_the_exact_amount_is_applied_to_late_then_ordinary_then_principal():
    assert DUE.total == money("109.77")
    assert DUE.apply(money("109.77")) == DUE


@pytest.mark.parametrize(
    ("amount", "code"),
    [
        ("109.68", "PARTIAL_PAYMENT_NOT_ALLOWED"),
        ("0.09", "PARTIAL_PAYMENT_NOT_ALLOWED"),
        ("110", "PAYMENT_EXCEEDS_DUE"),
    ],
)
def test_any_other_amount_is_rejected(amount, code):
    with pytest.raises(BusinessError) as error:
        DUE.apply(money(amount))

    assert (error.value.code, error.value.field) == (code, "amount")
    assert error.value.details == {"due": "109.77"}


def test_late_interest_is_the_late_rate_for_the_days_late():
    # 109.68 x ((1 + 10%)^(3/360) - 1) = 0.0871...
    assert late_interest(money("109.68"), Rate.from_percent(Decimal("10")), 3) == money("0.09")
    assert late_interest(money("109.68"), Rate.from_percent(Decimal("10")), 0) == money("0")


def test_interest_for_the_days_used_and_its_savings():
    tea = Rate.from_percent(Decimal("75"))

    # The report's test N°1 term: S/ 400 for 42 days.
    full = interest_for_days(money("400"), tea, 42)
    early = interest_for_days(money("400"), tea, 21)

    assert (full, early) == (money("26.99"), money("13.27"))
    assert savings(full, early) == money("13.72")
    assert savings(early, full) == money("0")


def cycle() -> BillingCycle:
    return BillingCycle.open(1, 2, cycle_period_of(date(2026, 10, 15), 14, 26))


def test_a_closed_cycle_becomes_overdue_after_its_payment_date():
    closed = cycle()
    closed.close(StatementTotals(money("400"), money("26.99")), datetime(2026, 11, 15, tzinfo=UTC))

    assert (closed.status, closed.total) == (CycleStatus.CLOSED, money("426.99"))
    assert closed.status_on(date(2026, 11, 26)) == CycleStatus.CLOSED
    assert closed.status_on(date(2026, 11, 27)) == CycleStatus.OVERDUE


def test_a_cycle_with_nothing_to_pay_is_paid_when_it_closes():
    empty = cycle()
    empty.close(StatementTotals(money("0"), money("0")), datetime(2026, 11, 15, tzinfo=UTC))

    assert empty.status == CycleStatus.PAID


def test_a_cycle_closes_the_day_after_its_cutoff():
    open_cycle = cycle()

    assert not open_cycle.is_due_for_closing(date(2026, 11, 14))
    assert open_cycle.is_due_for_closing(date(2026, 11, 15))
