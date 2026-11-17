import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.iam.application.ports.customer_directory import CustomerDirectory
from app.iam.application.ports.password_hasher import PasswordHasher
from app.iam.application.ports.password_reset_notifier import PasswordResetNotifier
from app.iam.domain.model.aggregates.password_reset_token import PasswordResetToken
from app.iam.domain.model.aggregates.user import normalize_username
from app.iam.domain.model.commands.redeem_access_code_command import RedeemAccessCodeCommand
from app.iam.domain.model.commands.reset_forgotten_password_command import (
    ResetForgottenPasswordCommand,
)
from app.iam.domain.model.value_objects.password import ensure_valid_password
from app.iam.domain.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.iam.domain.repositories.user_repository import UserRepository
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Role
from app.shared.infrastructure.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

# 32 random bytes, so a token cannot be guessed within its lifetime.
RESET_TOKEN_BYTES = 32


def hash_reset_token(token: str) -> str:
    # The token is random and long, so a fast hash is enough: there is nothing to brute force.
    return hashlib.sha256(token.encode()).hexdigest()


class PasswordRecoveryService:
    """Lets users who cannot sign in choose a new password.

    Administrators get a link by email. Customers sign in with their DNI and have no email,
    so they use the access code a store hands them in person.
    """

    def __init__(
        self,
        users: UserRepository,
        reset_tokens: PasswordResetTokenRepository,
        hasher: PasswordHasher,
        notifier: PasswordResetNotifier,
        customers: CustomerDirectory,
        unit_of_work: UnitOfWork,
        token_minutes: int,
        frontend_url: str,
    ) -> None:
        self._users = users
        self._reset_tokens = reset_tokens
        self._hasher = hasher
        self._notifier = notifier
        self._customers = customers
        self._unit_of_work = unit_of_work
        self._token_lifetime = timedelta(minutes=token_minutes)
        self._frontend_url = frontend_url.rstrip("/")

    async def request_reset(self, email: str) -> None:
        """Email a reset link if the email belongs to an active administrator.

        Says nothing either way, so the endpoint cannot be used to find out who has an account.
        """
        user = await self._users.find_by_username(normalize_username(email))
        if user is None or user.id is None or not user.is_active or user.role == Role.CUSTOMER:
            return
        token = secrets.token_urlsafe(RESET_TOKEN_BYTES)
        await self._reset_tokens.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_reset_token(token),
                expires_at=datetime.now(UTC) + self._token_lifetime,
            )
        )
        await self._unit_of_work.commit()
        link = f"{self._frontend_url}/reset-password?{urlencode({'token': token})}"
        try:
            await self._notifier.send_reset_link(user.username, link)
        except Exception:
            # Failing here would tell the caller that the account exists; the user can retry.
            logger.exception("Could not send the password reset email to user %s", user.id)

    async def reset(self, command: ResetForgottenPasswordCommand) -> None:
        ensure_valid_password(command.new_password, field="new_password")
        now = datetime.now(UTC)
        token = await self._reset_tokens.find_by_hash(hash_reset_token(command.token))
        user = await self._users.find_by_id(token.user_id) if token else None
        if token is None or user is None or not token.is_usable(now) or not user.is_active:
            raise BusinessError(
                "INVALID_RESET_TOKEN",
                "The password reset link is invalid or has expired. Request a new one.",
                field="token",
            )
        user.change_password(await self._hasher.hash(command.new_password))
        await self._users.update(user)
        await self._reset_tokens.use_all_of_user(token.user_id, now)
        await self._unit_of_work.commit()

    async def reset_with_access_code(self, command: RedeemAccessCodeCommand, now: datetime) -> None:
        """Set the password a customer chose, for the access code of one of their stores.

        The store that issued the code never learns the password.
        """
        # Checked first, so a password that is too short does not spend the code.
        ensure_valid_password(command.new_password, field="new_password")
        user_id = await self._customers.redeem_access_code(command.dni, command.code, now)
        user = await self._users.find_by_id(user_id)
        if user is None:
            raise ValueError("The customer has no user.")
        user.change_password(await self._hasher.hash(command.new_password))
        await self._users.update(user)
        await self._unit_of_work.commit()
