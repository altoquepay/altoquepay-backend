"""A person who buys on credit, in one store or several, with one user to see their accounts."""

from dataclasses import dataclass

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni

NAMES_MAXIMUM_LENGTH = 100


@dataclass
class Customer:
    dni: Dni
    first_names: str
    last_names: str
    user_id: int
    phone: str | None = None
    address: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.first_names = required_name(self.first_names, "first_names")
        self.last_names = required_name(self.last_names, "last_names")
        self.phone = blank_as_none(self.phone)
        self.address = blank_as_none(self.address)


def required_name(name: str, field: str) -> str:
    name = name.strip()
    if not 1 <= len(name) <= NAMES_MAXIMUM_LENGTH:
        raise BusinessError(
            "INVALID_NAME",
            f"The name must have between 1 and {NAMES_MAXIMUM_LENGTH} characters.",
            field=field,
        )
    return name


def blank_as_none(text: str | None) -> str | None:
    return (text or "").strip() or None
