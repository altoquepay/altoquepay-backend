"""Tests for the JWT validation dependencies."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.shared.interfaces.rest.error_handlers import register_error_handlers
from app.shared.interfaces.rest.security import (
    CurrentUser,
    Role,
    get_current_user,
    get_store_id,
    get_token_user,
    require_role,
)
from tests.authorization import authorization

probe_app = FastAPI()
register_error_handlers(probe_app)


@probe_app.get("/token-user")
async def read_token_user(user: Annotated[CurrentUser, Depends(get_token_user)]):
    return {"user_id": user.user_id}


@probe_app.get("/current-user")
async def read_current_user(user: Annotated[CurrentUser, Depends(get_current_user)]):
    return {"user_id": user.user_id, "role": user.role}


@probe_app.get("/admin")
async def read_admin(user: Annotated[CurrentUser, Depends(require_role(Role.SYSTEM_ADMIN))]):
    return {"user_id": user.user_id}


@probe_app.get("/store")
async def read_store(store_id: Annotated[int, Depends(get_store_id)]):
    return {"store_id": store_id}


client = TestClient(probe_app)


def test_valid_token_returns_the_user():
    response = client.get("/current-user", headers=authorization())
    assert response.status_code == 200
    assert response.json() == {"user_id": "7", "role": "STORE_ADMIN"}


def test_missing_token_is_unauthorized_with_the_common_format():
    response = client.get("/current-user")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "invalid_headers",
    [
        lambda: authorization(exp=datetime.now(UTC) - timedelta(minutes=5)),
        lambda: authorization(exp=None),
        lambda: authorization(sub=None),
        lambda: authorization(sub=7),
        lambda: authorization(role=None),
        lambda: authorization(role="SUPER_ADMIN"),
        lambda: authorization(must_change_password=None),
        lambda: authorization(secret="a-different-secret-of-at-least-32-bytes"),
        lambda: {"Authorization": "Bearer not-a-token"},
    ],
    ids=[
        "expired",
        "no-exp",
        "no-sub",
        "numeric-sub",
        "no-role",
        "unknown-role",
        "no-must-change-password",
        "wrong-secret",
        "malformed",
    ],
)
def test_invalid_tokens_are_unauthorized(invalid_headers):
    response = client.get("/current-user", headers=invalid_headers())
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_unsigned_token_is_rejected():
    token = jwt.encode(
        {
            "sub": "7",
            "role": "SYSTEM_ADMIN",
            "must_change_password": False,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key=None,
        algorithm="none",
    )
    response = client.get("/current-user", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_pending_password_change_blocks_everything_but_the_token_user():
    headers = authorization(must_change_password=True)

    blocked = client.get("/current-user", headers=headers)

    assert blocked.status_code == 403
    assert blocked.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    assert client.get("/token-user", headers=headers).status_code == 200


def test_require_role_rejects_other_roles():
    response = client.get("/admin", headers=authorization())
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_require_role_accepts_an_allowed_role():
    assert client.get("/admin", headers=authorization(role="SYSTEM_ADMIN")).status_code == 200


def test_store_id_comes_from_the_token():
    response = client.get("/store", params={"store_id": 99}, headers=authorization())
    assert response.json() == {"store_id": 3}


def test_store_id_is_forbidden_for_tokens_without_a_store():
    response = client.get("/store", headers=authorization(role="CUSTOMER", store_id=None))
    assert response.status_code == 403
