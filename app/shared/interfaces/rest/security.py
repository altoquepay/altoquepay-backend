"""FastAPI dependencies that validate the JWT issued by the iam context.

No bounded context depends on the iam tables to authorize: two facades are asked on every
request. get_signed_in_user asks iam whether the user still has the password of the token, and
get_store_id asks stores whether the store is still active.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.iam.interfaces.acl.iam_facade import IamFacade
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Role
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.stores.interfaces.acl.stores_facade import StoresFacade

JWT_ALGORITHM = "HS256"
ACTIVE_STORE_STATUS = "ACTIVE"
REQUIRED_CLAIMS = ["exp", "sub", "role", "must_change_password"]

bearer_token = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: Role
    must_change_password: bool
    store_id: int | None = None
    customer_id: int | None = None
    password_version: int = 0


async def get_token_user(token: Annotated[str, Depends(bearer_token)]) -> CurrentUser:
    """Return the claims of a valid token. Routes use get_signed_in_user, which checks more."""
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": REQUIRED_CLAIMS},
        )
        return CurrentUser(
            user_id=claims["sub"],
            role=Role(claims["role"]),
            must_change_password=claims["must_change_password"],
            store_id=claims.get("store_id"),
            customer_id=claims.get("customer_id"),
            password_version=claims.get("password_version", 0),
        )
    except (jwt.InvalidTokenError, ValueError) as error:
        raise HTTPException(
            401, "Could not validate credentials.", headers={"WWW-Authenticate": "Bearer"}
        ) from error


async def get_signed_in_user(
    user: Annotated[CurrentUser, Depends(get_token_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> CurrentUser:
    """Return the token's user, unless their password changed after the token was issued.

    The version is read on every request, so a reset, a change or a store's access code blocks
    the tokens of whoever knew the previous password. Only change-password and me use this
    directly, since they must work before a temporary password is changed.
    """
    iam = IamFacade(unit_of_work)
    if not await iam.is_password_current(int(user.user_id), user.password_version):
        raise HTTPException(
            401, "Could not validate credentials.", headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def get_current_user(
    user: Annotated[CurrentUser, Depends(get_signed_in_user)],
) -> CurrentUser:
    """Return the token's user, unless they still have to change their temporary password."""
    if user.must_change_password:
        raise BusinessError(
            "PASSWORD_CHANGE_REQUIRED", "You must change your password to continue.", status=403
        )
    return user


def require_role(*allowed_roles: Role) -> Callable[..., Awaitable[CurrentUser]]:
    """Create a dependency that only lets users with one of the given roles through."""

    async def get_user_with_allowed_role(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(403, "You do not have permission to perform this action.")
        return user

    return get_user_with_allowed_role


async def get_store_id(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> int:
    """Return the store of the token, if it is still active. Never read it from the body or URL.

    The status is read on every request, so deactivating a store blocks tokens already issued.
    """
    if user.store_id is None:
        raise HTTPException(403, "You do not have permission to perform this action.")
    store = await StoresFacade(unit_of_work).get_store_status(user.store_id)
    if store.status != ACTIVE_STORE_STATUS:
        raise BusinessError("STORE_INACTIVE", "The store of this user is not active.", status=403)
    return user.store_id


get_customer = require_role(Role.CUSTOMER)
