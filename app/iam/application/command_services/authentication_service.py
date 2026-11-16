from dataclasses import dataclass

from app.iam.application.ports.customer_directory import CustomerDirectory
from app.iam.application.ports.password_hasher import PasswordHasher
from app.iam.application.ports.store_directory import StoreDirectory
from app.iam.application.ports.token_service import TokenClaims, TokenService
from app.iam.domain.model.aggregates.user import User, normalize_username
from app.iam.domain.model.commands.change_password_command import ChangePasswordCommand
from app.iam.domain.model.commands.sign_in_command import SignInCommand
from app.iam.domain.model.value_objects.password import (
    PASSWORD_MAXIMUM_LENGTH,
    ensure_valid_password,
)
from app.iam.domain.repositories.user_repository import UserRepository
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Role
from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class SignedInUser:
    user: User
    access_token: str


def invalid_credentials() -> BusinessError:
    # One message for unknown users and wrong passwords, so it does not reveal who has an account.
    return BusinessError(
        "INVALID_CREDENTIALS", "The username or password is incorrect.", status=401
    )


class AuthenticationService:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        stores: StoreDirectory,
        customers: CustomerDirectory,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._stores = stores
        self._customers = customers
        self._unit_of_work = unit_of_work

    async def sign_in(self, command: SignInCommand) -> SignedInUser:
        # No stored password is that long, and hashing it would only waste time.
        if len(command.password) > PASSWORD_MAXIMUM_LENGTH:
            raise invalid_credentials()
        user = await self._users.find_by_username(normalize_username(command.username))
        if user is None:
            await self._hasher.verify_without_user(command.password)
            raise invalid_credentials()
        matches, updated_hash = await self._hasher.verify(command.password, user.password_hash)
        if not matches:
            raise invalid_credentials()
        self._ensure_active(user)
        access_token = await self._issue_token(user)
        if updated_hash is not None:
            # The hash used outdated parameters; store the stronger one while we know the password.
            user.password_hash = updated_hash
            await self._users.update(user)
            await self._unit_of_work.commit()
        return SignedInUser(user, access_token)

    async def change_password(self, command: ChangePasswordCommand) -> SignedInUser:
        """Change the password and return a new token, since the old one may still be blocked."""
        user = await self._users.find_by_id(command.user_id)
        if user is None:
            raise BusinessError("NOT_FOUND", "The user does not exist.", status=404)
        self._ensure_active(user)
        if not await self._password_matches(user, command.current_password):
            raise BusinessError(
                "INVALID_CURRENT_PASSWORD",
                "The current password is incorrect.",
                field="current_password",
            )
        ensure_valid_password(command.new_password, field="new_password")
        if command.new_password == command.current_password:
            raise BusinessError(
                "PASSWORD_UNCHANGED",
                "The new password must be different from the current one.",
                field="new_password",
            )
        user.change_password(await self._hasher.hash(command.new_password))
        access_token = await self._issue_token(user)
        await self._users.update(user)
        await self._unit_of_work.commit()
        return SignedInUser(user, access_token)

    async def _password_matches(self, user: User, password: str) -> bool:
        if len(password) > PASSWORD_MAXIMUM_LENGTH:
            return False
        matches, _updated_hash = await self._hasher.verify(password, user.password_hash)
        return matches

    @staticmethod
    def _ensure_active(user: User) -> None:
        if not user.is_active:
            raise BusinessError("USER_INACTIVE", "This user has been deactivated.", status=403)

    async def _issue_token(self, user: User) -> str:
        if user.id is None:
            raise ValueError("Only a stored user can sign in.")
        customer_id = None
        if user.role == Role.STORE_ADMIN:
            if user.store_id is None or not await self._stores.is_store_active(user.store_id):
                raise BusinessError(
                    "STORE_INACTIVE", "The store of this user is not active.", status=403
                )
        elif user.role == Role.CUSTOMER:
            customer_id = await self._customers.get_customer_id(user.id)
        return self._tokens.issue(
            TokenClaims(
                user_id=user.id,
                role=user.role,
                must_change_password=user.must_change_password,
                store_id=user.store_id,
                customer_id=customer_id,
            )
        )
