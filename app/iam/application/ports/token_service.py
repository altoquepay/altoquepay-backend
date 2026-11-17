from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.shared.domain.value_objects import Role


@dataclass(frozen=True)
class TokenClaims:
    """What every other context learns about the user from the token, without asking iam."""

    user_id: int
    role: Role
    must_change_password: bool
    store_id: int | None = None
    customer_id: int | None = None
    password_version: int = 0


class TokenService(ABC):
    @abstractmethod
    def issue(self, claims: TokenClaims) -> str:
        """Return a signed access token that expires after the configured lifetime."""
