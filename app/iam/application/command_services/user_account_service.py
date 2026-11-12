from app.iam.application.ports.password_hasher import PasswordHasher
from app.iam.domain.model.aggregates.user import User, normalize_username
from app.iam.domain.model.value_objects.email import Email
from app.iam.domain.model.value_objects.password import ensure_valid_password
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.domain.services.temporary_password import generate_temporary_password
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni


class UserAccountService:
    """Creates users for other contexts. It never commits: the use case that calls it does."""

    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def create_store_admin(
        self, email: str, full_name: str, password: str, store_id: int
    ) -> User:
        valid_email = Email(email)
        ensure_valid_password(password)
        # shortcut: two simultaneous registrations can both pass this check, and the unique
        # constraint then rejects one with a 500; map IntegrityError to 409 if that ever happens.
        if await self._users.exists_by_username(valid_email.value):
            raise BusinessError(
                "EMAIL_TAKEN", "The email is already registered.", field="email", status=409
            )
        user = User.store_admin(valid_email, full_name, await self._hasher.hash(password), store_id)
        await self._users.add(user)
        return user

    async def create_customer_user(self, dni: str) -> tuple[User, str]:
        """Return the new user and its temporary password, which is never stored in plain text."""
        valid_dni = Dni(dni.strip())
        if await self._users.exists_by_username(valid_dni.value):
            raise BusinessError(
                "USERNAME_TAKEN",
                "A user with this DNI already exists.",
                field="dni",
                status=409,
            )
        temporary_password = generate_temporary_password()
        user = User.customer(valid_dni, await self._hasher.hash(temporary_password))
        await self._users.add(user)
        return user, temporary_password

    async def reset_password(self, user_id: int) -> tuple[User, str]:
        """Return the user and its new temporary password."""
        user = await self._users.find_by_id(user_id)
        if user is None:
            raise BusinessError("NOT_FOUND", "The user does not exist.", status=404)
        temporary_password = generate_temporary_password()
        user.assign_temporary_password(await self._hasher.hash(temporary_password))
        await self._users.update(user)
        return user, temporary_password

    async def find_by_username(self, username: str) -> User | None:
        return await self._users.find_by_username(normalize_username(username))

    async def create_first_system_admin(self, email: str, password: str) -> User | None:
        """Create the system administrator of the settings, or return None if it exists."""
        valid_email = Email(email)
        if await self._users.exists_by_username(valid_email.value):
            return None
        ensure_valid_password(password, field="FIRST_ADMIN_PASSWORD")
        user = User.system_admin(valid_email, await self._hasher.hash(password))
        await self._users.add(user)
        return user
