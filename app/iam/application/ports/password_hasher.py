from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    async def hash(self, password: str) -> str: ...

    @abstractmethod
    async def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        """Return whether the password matches, and a new hash if the old one is outdated."""

    @abstractmethod
    async def verify_without_user(self, password: str) -> None:
        """Take as long as a real check, so response times do not reveal which usernames exist."""
