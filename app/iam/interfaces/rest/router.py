from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.iam.application.command_services.authentication_service import (
    AuthenticationService,
    SignedInUser,
)
from app.iam.application.command_services.password_recovery_service import (
    PasswordRecoveryService,
)
from app.iam.application.query_services.user_query_service import UserQueryService
from app.iam.domain.model.commands.change_password_command import ChangePasswordCommand
from app.iam.domain.model.commands.redeem_access_code_command import RedeemAccessCodeCommand
from app.iam.domain.model.commands.reset_forgotten_password_command import (
    ResetForgottenPasswordCommand,
)
from app.iam.domain.model.commands.sign_in_command import SignInCommand
from app.iam.interfaces.rest.dependencies import (
    get_authentication_service,
    get_password_recovery_service,
    get_user_query_service,
)
from app.iam.interfaces.rest.resources.auth_resources import (
    AccessTokenResource,
    ChangePasswordResource,
    CurrentUserResource,
    ForgotPasswordResource,
    RedeemAccessCodeResource,
    ResetPasswordResource,
)
from app.iam.interfaces.rest.sign_in_attempts import limit_sign_in_attempts
from app.shared.interfaces.rest.business_date import get_business_now
from app.shared.interfaces.rest.security import CurrentUser, get_signed_in_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# change-password and me must stay reachable while a temporary password blocks everything else.
TokenUser = Annotated[CurrentUser, Depends(get_signed_in_user)]


def to_access_token_resource(signed_in: SignedInUser) -> AccessTokenResource:
    return AccessTokenResource(
        access_token=signed_in.access_token,
        role=signed_in.user.role,
        must_change_password=signed_in.user.must_change_password,
    )


@router.post("/login", dependencies=[Depends(limit_sign_in_attempts)])
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> AccessTokenResource:
    """Sign in with an email (administrators) or a DNI (customers), sent as a form.

    The form is the OAuth2 password flow, so the Authorize button of Swagger works too.
    """
    signed_in = await service.sign_in(SignInCommand(form.username, form.password))
    return to_access_token_resource(signed_in)


@router.post("/change-password")
async def change_password(
    resource: ChangePasswordResource,
    user: TokenUser,
    service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> AccessTokenResource:
    """Change the password and return a new token, which no longer requires a change."""
    command = ChangePasswordCommand(
        user_id=int(user.user_id),
        current_password=resource.current_password,
        new_password=resource.new_password,
    )
    return to_access_token_resource(await service.change_password(command))


@router.get("/me")
async def me(
    user: TokenUser,
    service: Annotated[UserQueryService, Depends(get_user_query_service)],
) -> CurrentUserResource:
    """Return the signed-in user, so the frontend knows which screens to show."""
    stored_user = await service.get_by_id(int(user.user_id))
    return CurrentUserResource(
        id=int(user.user_id),
        username=stored_user.username,
        full_name=stored_user.full_name,
        role=stored_user.role,
        store_id=stored_user.store_id,
        customer_id=user.customer_id,
        must_change_password=stored_user.must_change_password,
    )


# Shares the sign-in budget of the IP, so a script cannot flood an inbox with reset emails.
@router.post("/forgot-password", status_code=204, dependencies=[Depends(limit_sign_in_attempts)])
async def forgot_password(
    resource: ForgotPasswordResource,
    service: Annotated[PasswordRecoveryService, Depends(get_password_recovery_service)],
) -> None:
    """Email a reset link to an administrator. Answers the same whether the email exists or not."""
    await service.request_reset(resource.email)


@router.post("/reset-password", status_code=204)
async def reset_password(
    resource: ResetPasswordResource,
    service: Annotated[PasswordRecoveryService, Depends(get_password_recovery_service)],
) -> None:
    """Choose a new password with the token of the reset link. Each link works once."""
    await service.reset(ResetForgottenPasswordCommand(resource.token, resource.new_password))


@router.post("/redeem-access-code", status_code=204)
async def redeem_access_code(
    resource: RedeemAccessCodeResource,
    service: Annotated[PasswordRecoveryService, Depends(get_password_recovery_service)],
    now: Annotated[datetime, Depends(get_business_now)],
) -> None:
    """Let a customer choose their password with the access code a store handed them.

    It links that store to their portal and unlinks their other stores, since only the store of
    the code vouches for who holds the new password. A customer who knows their password adds
    a store with /me/stores/link instead.
    """
    command = RedeemAccessCodeCommand(resource.dni, resource.code, resource.new_password)
    await service.reset_with_access_code(command, now)
