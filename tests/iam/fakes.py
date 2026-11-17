"""In-memory stand-ins for the ports of the iam use cases, for tests without a database."""

from dataclasses import replace
from datetime import datetime

from app.iam.application.ports.customer_directory import CustomerDirectory
from app.iam.application.ports.password_hasher import PasswordHasher
from app.iam.application.ports.password_reset_notifier import PasswordResetNotifier
from app.iam.application.ports.store_directory import StoreDirectory
from app.iam.application.ports.token_service import TokenClaims, TokenService
from app.iam.domain.model.aggregates.password_reset_token import PasswordResetToken
from app.iam.domain.model.aggregates.user import User
from app.iam.domain.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.iam.domain.repositories.user_repository import UserRepository


class InMemoryUsers(UserRepository):
    def __init__(self) -> None:
        self.stored: dict[int, User] = {}

    async def find_by_id(self, user_id: int) -> User | None:
        user = self.stored.get(user_id)
        return replace(user) if user else None

    async def find_by_username(self, username: str) -> User | None:
        return next((replace(u) for u in self.stored.values() if u.username == username), None)

    async def exists_by_username(self, username: str) -> bool:
        return await self.find_by_username(username) is not None

    async def add(self, user: User) -> None:
        user.id = len(self.stored) + 1
        self.stored[user.id] = replace(user)

    async def update(self, user: User) -> None:
        assert user.id in self.stored
        self.stored[user.id] = replace(user)


class InMemoryResetTokens(PasswordResetTokenRepository):
    def __init__(self) -> None:
        self.stored: list[PasswordResetToken] = []

    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return next((t for t in self.stored if t.token_hash == token_hash), None)

    async def add(self, token: PasswordResetToken) -> None:
        token.id = len(self.stored) + 1
        self.stored.append(token)

    async def use_all_of_user(self, user_id: int, now: datetime) -> None:
        for token in self.stored:
            if token.user_id == user_id and token.used_at is None:
                token.used_at = now


class PlainHasher(PasswordHasher):
    """Readable hashes; a hash made with outdated parameters starts with "old:"."""

    def __init__(self) -> None:
        self.checks_without_user = 0

    async def hash(self, password: str) -> str:
        return f"hashed:{password}"

    async def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        if password_hash == f"old:{password}":
            return True, await self.hash(password)
        return password_hash == f"hashed:{password}", None

    async def verify_without_user(self, password: str) -> None:
        self.checks_without_user += 1


class ClaimsAsToken(TokenService):
    def __init__(self) -> None:
        self.issued: list[TokenClaims] = []

    def issue(self, claims: TokenClaims) -> str:
        self.issued.append(claims)
        return f"token-{len(self.issued)}"


class FixedStores(StoreDirectory):
    def __init__(self, inactive_store_ids: set[int] | None = None) -> None:
        self.inactive_store_ids = inactive_store_ids or set()

    async def is_store_active(self, store_id: int) -> bool:
        return store_id not in self.inactive_store_ids


class FixedCustomers(CustomerDirectory):
    """Every access code is good and belongs to the customer whose user is 1."""

    def __init__(self) -> None:
        self.redeemed: list[tuple[str, str]] = []

    async def get_customer_id(self, user_id: int) -> int:
        return user_id * 100

    async def redeem_access_code(self, dni: str, code: str, now: datetime) -> int:
        self.redeemed.append((dni, code))
        return 1


class RecordingNotifier(PasswordResetNotifier):
    def __init__(self, fails: bool = False) -> None:
        self.sent: list[tuple[str, str]] = []
        self.fails = fails

    async def send_reset_link(self, email: str, link: str) -> None:
        if self.fails:
            raise ConnectionError("SMTP server is down")
        self.sent.append((email, link))


class CountingUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1
