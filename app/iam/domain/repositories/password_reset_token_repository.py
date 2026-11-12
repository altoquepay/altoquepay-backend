from abc import ABC, abstractmethod
from datetime import datetime

from app.iam.domain.model.aggregates.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None: ...

    @abstractmethod
    async def add(self, token: PasswordResetToken) -> None:
        """Store a new token and set its id."""

    @abstractmethod
    async def use_all_of_user(self, user_id: int, now: datetime) -> None:
        """Mark every unused token of a user as used, so older emails stop working."""
