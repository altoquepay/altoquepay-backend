"""Tests that the tokens iam issues are the ones the shared security dependencies accept."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.iam.application.ports.token_service import TokenClaims
from app.iam.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.iam.infrastructure.security.jwt_token_service import JwtTokenService
from app.shared.domain.value_objects import Role
from app.shared.infrastructure.config import get_settings
from app.shared.interfaces.rest.security import CurrentUser, get_token_user


@pytest.fixture
def service():
    return JwtTokenService(get_settings().jwt_secret, expire_minutes=60)


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        (
            TokenClaims(7, Role.STORE_ADMIN, must_change_password=False, store_id=3),
            CurrentUser("7", Role.STORE_ADMIN, False, store_id=3),
        ),
        (
            TokenClaims(9, Role.CUSTOMER, must_change_password=True, customer_id=4),
            CurrentUser("9", Role.CUSTOMER, True, customer_id=4),
        ),
        (
            TokenClaims(1, Role.SYSTEM_ADMIN, must_change_password=False),
            CurrentUser("1", Role.SYSTEM_ADMIN, False),
        ),
    ],
)
async def test_security_reads_back_the_claims(service, claims, expected):
    assert await get_token_user(service.issue(claims)) == expected


def test_token_expires_after_the_configured_minutes(service):
    token = service.issue(TokenClaims(1, Role.SYSTEM_ADMIN, must_change_password=False))

    claims = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])

    lifetime = datetime.fromtimestamp(claims["exp"], UTC) - datetime.now(UTC)
    assert timedelta(minutes=59) < lifetime <= timedelta(minutes=60)
    assert "store_id" not in claims and "customer_id" not in claims


async def test_argon2_hashes_verify_only_the_right_password():
    hasher = Argon2PasswordHasher()

    password_hash = await hasher.hash("mi-clave-segura")

    assert password_hash.startswith("$argon2")
    assert await hasher.verify("mi-clave-segura", password_hash) == (True, None)
    assert (await hasher.verify("otra-clave", password_hash))[0] is False
    await hasher.verify_without_user("cualquier-clave")
