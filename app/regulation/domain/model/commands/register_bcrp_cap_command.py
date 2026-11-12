from dataclasses import dataclass
from datetime import date

from app.shared.domain.value_objects import Rate


@dataclass(frozen=True)
class RegisterBcrpCapCommand:
    max_tea: Rate
    valid_from: date
    valid_to: date
    registered_by: int
