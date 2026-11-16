from abc import ABC, abstractmethod

from app.iam.domain.model.aggregates.user import User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    async def find_by_username(self, username: str) -> User | None:
        """Find the user with that username, already normalized."""

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool: ...

    @abstractmethod
    async def add(self, user: User) -> None:
        """Store a new user and set its id."""

    @abstractmethod
    async def update(self, user: User) -> None:
        """Store the changes of a user that already has an id."""
