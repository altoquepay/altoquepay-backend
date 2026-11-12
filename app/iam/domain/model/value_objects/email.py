import re
from dataclasses import dataclass

from app.shared.domain.errors import BusinessError

EMAIL_MAXIMUM_LENGTH = 254
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True)
class Email:
    """An email address, lowercased so the same mailbox is never registered twice."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if len(normalized) > EMAIL_MAXIMUM_LENGTH or not EMAIL_PATTERN.fullmatch(normalized):
            raise BusinessError("INVALID_EMAIL", "The email address is not valid.", field="email")
        object.__setattr__(self, "value", normalized)
