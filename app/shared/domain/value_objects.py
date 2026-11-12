"""Immutable value objects that are valid from the moment they are created."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.shared.domain.errors import BusinessError

MONEY_STEP = Decimal("0.01")
RATE_PERCENT_STEP = Decimal("0.0000001")

# Upper bounds of the NUMERIC(12,2) and NUMERIC(12,7) database columns.
MONEY_LIMIT = Decimal("10000000000")
RATE_PERCENT_LIMIT = Decimal("100000")


class Role(StrEnum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    STORE_ADMIN = "STORE_ADMIN"
    CUSTOMER = "CUSTOMER"


@dataclass(frozen=True)
class Money:
    """A non-negative amount in soles, rounded to 2 decimals."""

    amount: Decimal

    def __post_init__(self) -> None:
        # Rejecting float keeps binary rounding errors out of the financial calculations.
        if (
            not isinstance(self.amount, Decimal)
            or not self.amount.is_finite()
            or not 0 <= self.amount < MONEY_LIMIT
        ):
            raise BusinessError(
                "INVALID_AMOUNT",
                "The amount must be a non-negative number within the allowed range.",
                field="amount",
            )
        # abs only turns -0 into 0, since negative amounts were rejected above.
        rounded_amount = abs(self.amount).quantize(MONEY_STEP, ROUND_HALF_UP)
        object.__setattr__(self, "amount", rounded_amount)


@dataclass(frozen=True)
class Rate:
    """A non-negative interest rate kept as a fraction at full precision (75% is 0.75)."""

    fraction: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fraction, Decimal)
            or not self.fraction.is_finite()
            # Dividing the limit, not multiplying the fraction, so huge fractions cannot overflow.
            or not 0 <= self.fraction < RATE_PERCENT_LIMIT / 100
        ):
            raise BusinessError(
                "INVALID_RATE",
                "The rate must be a non-negative number within the allowed range.",
                field="rate",
            )

    @classmethod
    def from_percent(cls, percent: Decimal) -> "Rate":
        """Create a rate from the percentage used by the API and the database."""
        return cls(percent / 100)

    @property
    def percent(self) -> Decimal:
        """The percentage rounded to 7 decimals, as it is displayed and stored."""
        return (self.fraction * 100).quantize(RATE_PERCENT_STEP, ROUND_HALF_UP)


@dataclass(frozen=True)
class Dni:
    """A Peruvian national identity number. Kept as text to preserve leading zeros."""

    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9]{8}", self.value):
            raise BusinessError("INVALID_DNI", "The DNI must have 8 digits.", field="dni")


@dataclass(frozen=True)
class Ruc:
    """A Peruvian taxpayer number. Kept as text to preserve leading zeros."""

    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9]{11}", self.value):
            raise BusinessError("INVALID_RUC", "The RUC must have 11 digits.", field="ruc")
