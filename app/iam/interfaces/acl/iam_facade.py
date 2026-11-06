"""The only way other bounded contexts may reach the iam context."""

from dataclasses import dataclass

from app.shared.domain.value_objects import Role
from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class TemporaryCredentials:
    user_id: int
    username: str
    temporary_password: str


@dataclass(frozen=True)
class UserSummary:
    user_id: int
    username: str
    role: Role
    is_active: bool


class IamFacade:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def create_store_admin(
        self, email: str, full_name: str, password: str, store_id: int
    ) -> int:
        """Create the administrator of a store and return its user id.

        The password was chosen by the user, so no change is required on first login.
        Raises EMAIL_TAKEN (409) if the email is already registered.
        """
        raise NotImplementedError

    async def create_customer_user(self, dni: str) -> TemporaryCredentials:
        """Create a customer user named after the DNI, who must change the temporary password."""
        raise NotImplementedError

    async def reset_password(self, user_id: int) -> TemporaryCredentials:
        """Replace the password with a temporary one that must be changed on next login."""
        raise NotImplementedError

    async def find_user_by_username(self, username: str) -> UserSummary | None:
        """Return the user with that username, or None if there is none."""
        raise NotImplementedError
