from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerCredentials:
    """The temporary password is shown once, so the store can hand it to the customer."""

    user_id: int
    username: str
    temporary_password: str


class CustomerUsers(ABC):
    """The users customers sign in with, answered by the iam context. None of it commits."""

    @abstractmethod
    async def find_user_id(self, username: str) -> int | None: ...

    @abstractmethod
    async def create(self, dni: str) -> CustomerCredentials: ...

    @abstractmethod
    async def reset_password(self, user_id: int) -> CustomerCredentials: ...
