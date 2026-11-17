from abc import ABC, abstractmethod


class CustomerUsers(ABC):
    """The users customers sign in with, answered by the iam context. None of it commits."""

    @abstractmethod
    async def find_user_id(self, username: str) -> int | None: ...

    @abstractmethod
    async def create(self, dni: str) -> int:
        """Create the user of a new person and return its id. Nobody knows its password yet."""
