"""Creates the first system administrator, who registers the BCRP caps and nobody else can."""

import logging

from sqlalchemy.exc import IntegrityError

from app.iam.application.command_services.user_account_service import UserAccountService
from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.iam.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


async def create_first_system_admin() -> None:
    """Create the administrator of FIRST_ADMIN_EMAIL if missing. They must change the password."""
    settings = get_settings()
    if not settings.first_admin_email or not settings.first_admin_password:
        return
    async with UnitOfWork(session_factory) as unit_of_work:
        accounts = UserAccountService(
            UserRepositoryImpl(unit_of_work.session), Argon2PasswordHasher()
        )
        try:
            admin = await accounts.create_first_system_admin(
                settings.first_admin_email, settings.first_admin_password
            )
            await unit_of_work.commit()
        except IntegrityError:
            # Another worker created it at the same moment.
            return
        if admin is not None:
            logger.info("Created the first system administrator, %s.", admin.username)
