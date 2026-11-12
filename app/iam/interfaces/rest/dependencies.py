from typing import Annotated

from fastapi import Depends

from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.iam.application.command_services.authentication_service import AuthenticationService
from app.iam.application.command_services.password_recovery_service import (
    PasswordRecoveryService,
)
from app.iam.application.ports.password_reset_notifier import PasswordResetNotifier
from app.iam.application.query_services.user_query_service import UserQueryService
from app.iam.infrastructure.acl.external_customers import ExternalCustomers
from app.iam.infrastructure.acl.external_stores import ExternalStores
from app.iam.infrastructure.notifications.smtp_password_reset_notifier import (
    SmtpPasswordResetNotifier,
)
from app.iam.infrastructure.persistence.password_reset_token_repository_impl import (
    PasswordResetTokenRepositoryImpl,
)
from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.iam.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.iam.infrastructure.security.jwt_token_service import JwtTokenService
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.stores.interfaces.acl.stores_facade import StoresFacade


def get_password_reset_notifier() -> PasswordResetNotifier:
    return SmtpPasswordResetNotifier(get_settings())


def get_authentication_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> AuthenticationService:
    settings = get_settings()
    return AuthenticationService(
        users=UserRepositoryImpl(unit_of_work.session),
        hasher=Argon2PasswordHasher(),
        tokens=JwtTokenService(settings.jwt_secret, settings.jwt_expire_minutes),
        stores=ExternalStores(StoresFacade(unit_of_work)),
        customers=ExternalCustomers(CustomersFacade(unit_of_work)),
        unit_of_work=unit_of_work,
    )


def get_password_recovery_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    notifier: Annotated[PasswordResetNotifier, Depends(get_password_reset_notifier)],
) -> PasswordRecoveryService:
    settings = get_settings()
    return PasswordRecoveryService(
        users=UserRepositoryImpl(unit_of_work.session),
        reset_tokens=PasswordResetTokenRepositoryImpl(unit_of_work.session),
        hasher=Argon2PasswordHasher(),
        notifier=notifier,
        unit_of_work=unit_of_work,
        token_minutes=settings.reset_token_minutes,
        frontend_url=settings.frontend_url,
    )


def get_user_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserQueryService:
    return UserQueryService(UserRepositoryImpl(unit_of_work.session))
