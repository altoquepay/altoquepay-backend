"""A single-use permission, sent by email, to choose a new password without the current one."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PasswordResetToken:
    """Only the hash of the token is kept, so a database leak gives no usable links."""

    user_id: int
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None
    id: int | None = None

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and now < self.expires_at

    def use(self, now: datetime) -> None:
        self.used_at = now
