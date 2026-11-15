"""Tests for the authentication endpoints against the migrated PostgreSQL database.

Every test shares one Unit of Work that never commits, so the users it creates disappear.
"""

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.iam.interfaces.acl.iam_facade import IamFacade
from app.iam.interfaces.rest.dependencies import get_password_reset_notifier
from app.main import app as application
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from tests.iam.fakes import RecordingNotifier
from tests.stored_store import add_store

ADMIN_EMAIL = "rosa@bodega-test.pe"
ADMIN_PASSWORD = "clave-de-rosa"
CUSTOMER_DNI = "70000001"


class RollbackUnitOfWork(UnitOfWork):
    async def commit(self) -> None:
        await self.session.flush()


@pytest.fixture
async def unit_of_work():
    async with RollbackUnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture
def notifier():
    return RecordingNotifier()


@pytest.fixture
async def client(unit_of_work, notifier, monkeypatch):
    async def customer_of_user(_facade, user_id: int) -> int:
        return 4

    # The customers context is not built yet.
    monkeypatch.setattr(CustomersFacade, "get_customer_id_by_user", customer_of_user)
    application.dependency_overrides[get_unit_of_work] = lambda: unit_of_work
    application.dependency_overrides[get_password_reset_notifier] = lambda: notifier
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    application.dependency_overrides.clear()


@pytest.fixture
async def store_id(unit_of_work) -> int:
    return (await add_store(unit_of_work)).id


@pytest.fixture
async def store_admin_id(unit_of_work, store_id):
    return await IamFacade(unit_of_work).create_store_admin(
        ADMIN_EMAIL, "Rosa Quispe", ADMIN_PASSWORD, store_id=store_id
    )


@pytest.fixture
async def customer_credentials(unit_of_work):
    return await IamFacade(unit_of_work).create_customer_user(CUSTOMER_DNI)


async def login(client, username: str, password: str):
    return await client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )


def bearer(response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_store_admin_signs_in_and_reads_their_profile(client, store_admin_id, store_id):
    signed_in = await login(client, ADMIN_EMAIL.upper(), ADMIN_PASSWORD)
    me = await client.get("/api/v1/auth/me", headers=bearer(signed_in))

    assert signed_in.status_code == 200
    assert signed_in.json() | {"access_token": "..."} == {
        "access_token": "...",
        "token_type": "bearer",
        "role": "STORE_ADMIN",
        "must_change_password": False,
    }
    assert me.json() == {
        "id": store_admin_id,
        "username": ADMIN_EMAIL,
        "full_name": "Rosa Quispe",
        "role": "STORE_ADMIN",
        "store_id": store_id,
        "customer_id": None,
        "must_change_password": False,
    }


async def test_wrong_password_is_rejected(client, store_admin_id):
    response = await login(client, ADMIN_EMAIL, "otra-clave")

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_customer_is_blocked_until_changing_the_temporary_password(
    client, customer_credentials
):
    signed_in = await login(client, CUSTOMER_DNI, customer_credentials.temporary_password)
    blocked = await client.get("/api/v1/bcrp-caps/current", headers=bearer(signed_in))
    me = await client.get("/api/v1/auth/me", headers=bearer(signed_in))
    changed = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": customer_credentials.temporary_password,
            "new_password": "mi-clave-segura",
        },
        headers=bearer(signed_in),
    )
    unblocked = await client.get("/api/v1/bcrp-caps/current", headers=bearer(changed))

    assert signed_in.json()["must_change_password"] is True
    assert (blocked.status_code, blocked.json()["code"]) == (403, "PASSWORD_CHANGE_REQUIRED")
    assert (me.json()["customer_id"], me.json()["must_change_password"]) == (4, True)
    assert (changed.status_code, changed.json()["must_change_password"]) == (200, False)
    assert unblocked.status_code != 403
    assert (await login(client, CUSTOMER_DNI, "mi-clave-segura")).status_code == 200


async def test_wrong_current_password_is_reported_on_its_field(client, customer_credentials):
    signed_in = await login(client, CUSTOMER_DNI, customer_credentials.temporary_password)

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "no-es-esta", "new_password": "mi-clave-segura"},
        headers=bearer(signed_in),
    )

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == (
        "INVALID_CURRENT_PASSWORD",
        "current_password",
    )


async def test_profile_and_password_change_require_a_token(client):
    me = await client.get("/api/v1/auth/me")
    changed = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "a", "new_password": "mi-clave-segura"},
    )

    assert (me.status_code, changed.status_code) == (401, 401)


async def test_forgotten_password_is_reset_through_the_emailed_link(
    client, notifier, store_admin_id
):
    requested = await client.post("/api/v1/auth/forgot-password", json={"email": ADMIN_EMAIL})
    token = parse_qs(urlparse(notifier.sent[0][1]).query)["token"][0]
    reset = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "clave-nueva"}
    )
    reused = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "otra-clave"}
    )

    assert (requested.status_code, reset.status_code) == (204, 204)
    assert (reused.status_code, reused.json()["code"]) == (422, "INVALID_RESET_TOKEN")
    assert (await login(client, ADMIN_EMAIL, "clave-nueva")).status_code == 200
    assert (await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)).status_code == 401


async def test_forgot_password_answers_the_same_for_unknown_emails(client, notifier):
    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nadie@bodega-test.pe"}
    )

    assert response.status_code == 204
    assert notifier.sent == []
