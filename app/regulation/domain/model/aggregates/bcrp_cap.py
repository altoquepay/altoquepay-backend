"""The maximum interest rates set by the BCRP for a validity period."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Rate

LATE_CAP_SHARE_OF_ORDINARY_CAP = Decimal("0.15")


@dataclass
class BcrpCap:
    """A cap is valid from its first to its last day, both included, and never changes."""

    max_tea: Rate
    valid_from: date
    valid_to: date
    created_by: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.max_tea.fraction <= 0:
            raise BusinessError(
                "INVALID_RATE", "The cap must be greater than zero.", field="max_tea"
            )
        if self.valid_to < self.valid_from:
            raise BusinessError(
                "INVALID_VALIDITY_PERIOD",
                "The validity period must end on or after its first day.",
                field="valid_to",
            )

    @property
    def max_late_tea(self) -> Rate:
        return Rate(self.max_tea.fraction * LATE_CAP_SHARE_OF_ORDINARY_CAP)

    def covers(self, on_date: date) -> bool:
        return self.valid_from <= on_date <= self.valid_to
