"""The only way other bounded contexts may reach the iam context."""

from dataclasses import dataclass

from app.iam.application.command_services.user_account_service import UserAccountService
from app.iam.domain.model.aggregates.user import User
from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.iam.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
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


def stored_id(user: User) -> int:
    if user.id is None:
        raise ValueError("The user was not stored.")
    return user.id


class IamFacade:
    """Never commits: the use case of the calling context does, once all its work succeeded."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._accounts = UserAccountService(
            UserRepositoryImpl(unit_of_work.session), Argon2PasswordHasher()
        )

    async def create_store_admin(
        self, email: str, full_name: str, password: str, store_id: int
    ) -> int:
        """Create the administrator of a store and return its user id.

        The password was chosen by the user, so no change is required on first login.
        Raises EMAIL_TAKEN (409) if the email is already registered, and INVALID_EMAIL,
        INVALID_FULL_NAME or INVALID_PASSWORD (422) if a value is not valid.
        """
        user = await self._accounts.create_store_admin(email, full_name, password, store_id)
        return stored_id(user)

    async def create_customer_user(self, dni: str) -> TemporaryCredentials:
        """Create a customer user named after the DNI, who must change the temporary password.

        Raises USERNAME_TAKEN (409) if the DNI already has a user: a person who buys in
        several stores has one user, so look it up first with find_user_by_username.
        """
        user, temporary_password = await self._accounts.create_customer_user(dni)
        return TemporaryCredentials(stored_id(user), user.username, temporary_password)

    async def reset_password(self, user_id: int) -> TemporaryCredentials:
        """Replace the password with a temporary one that must be changed on next login.

        Raises NOT_FOUND (404) if the user does not exist.
        """
        user, temporary_password = await self._accounts.reset_password(user_id)
        return TemporaryCredentials(stored_id(user), user.username, temporary_password)

    async def find_user_by_username(self, username: str) -> UserSummary | None:
        """Return the user with that username, or None if there is none."""
        user = await self._accounts.find_by_username(username)
        if user is None:
            return None
        return UserSummary(stored_id(user), user.username, user.role, user.is_active)
