"""A payment the store registers for a customer: what it covered and how it was applied."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money

ZERO = Money(Decimal(0))


class PaymentKind(StrEnum):
    # The single date purchases of a closed cycle, with late interest after its payment date.
    CYCLE_STATEMENT = "CYCLE_STATEMENT"
    # A weekly installment on or after its due date, with late interest when late.
    INSTALLMENT = "INSTALLMENT"
    # A weekly installment before its due date: the full installment, schedule unchanged.
    INSTALLMENT_ADVANCE = "INSTALLMENT_ADVANCE"
    # A single date purchase before its payment date: interest only for the days used.
    SINGLE_DATE_EARLY = "SINGLE_DATE_EARLY"
    # The rest of a weekly purchase: its balance plus interest since the last due date paid.
    FULL_PREPAYMENT = "FULL_PREPAYMENT"


@dataclass(frozen=True)
class PaymentBreakdown:
    """What a payment covers, in the order it is applied: late, ordinary, principal.

    savings is the interest the customer stopped owing by paying early; it is not charged.
    """

    late_interest: Money
    ordinary_interest: Money
    principal: Money
    savings: Money = field(default=ZERO)

    @property
    def total(self) -> Money:
        return Money(
            self.late_interest.amount + self.ordinary_interest.amount + self.principal.amount
        )

    def apply(self, amount: Money) -> "PaymentBreakdown":
        """Apply an amount: first to late interest, then ordinary interest, then principal.

        There are no partial payments, so the amount must cover all of it, and no more.
        """
        remaining = amount.amount
        applied = []
        for part in (self.late_interest, self.ordinary_interest, self.principal):
            taken = min(remaining, part.amount)
            applied.append(Money(taken))
            remaining -= taken
        if applied[2] != self.principal:
            raise BusinessError(
                "PARTIAL_PAYMENT_NOT_ALLOWED",
                f"The payment must cover the full amount due (S/ {self.total.amount}).",
                field="amount",
                details={"due": str(self.total.amount)},
            )
        if remaining > 0:
            raise BusinessError(
                "PAYMENT_EXCEEDS_DUE",
                f"The payment is more than the amount due (S/ {self.total.amount}).",
                field="amount",
                details={"due": str(self.total.amount)},
            )
        return PaymentBreakdown(applied[0], applied[1], applied[2], self.savings)


@dataclass
class Payment:
    """Exactly one target is set, the one its kind pays: a cycle, an installment or a purchase."""

    store_id: int
    account_id: int
    kind: PaymentKind
    paid_on: date
    breakdown: PaymentBreakdown
    created_by: int
    cycle_id: int | None = None
    installment_id: int | None = None
    purchase_id: int | None = None
    created_at: datetime | None = None
    id: int | None = None
