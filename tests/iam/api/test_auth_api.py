"""Tests for the authentication endpoints against the migrated PostgreSQL database.

Every test shares one Unit of Work that never commits, so the users it creates disappear.
"""

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from app.customers.domain.model.aggregates.customer import Customer
from app.customers.infrastructure.persistence.customer_repository_impl import (
    CustomerRepositoryImpl,
)
from app.iam.application.command_services.user_account_service import UserAccountService
from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.iam.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.iam.interfaces.acl.iam_facade import IamFacade
from app.iam.interfaces.rest.dependencies import get_password_reset_notifier
from app.iam.interfaces.rest.sign_in_attempts import MAXIMUM_ATTEMPTS
from app.main import app as application
from app.shared.domain.value_objects import Dni
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from tests.iam.fakes import RecordingNotifier
from tests.stored_store import add_store

ADMIN_EMAIL = "rosa@bodega-test.pe"
ADMIN_PASSWORD = "clave-de-rosa"
SYSTEM_ADMIN_EMAIL = "admin@altoquepay-test.pe"
FIRST_PASSWORD = "clave-inicial"
CUSTOMER_DNI = "70000001"
CUSTOMER_PASSWORD = "clave-de-cliente"


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
async def client(unit_of_work, notifier):
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
async def system_admin(unit_of_work) -> None:
    """The first administrator, created with a password from the settings that they must change."""
    accounts = UserAccountService(UserRepositoryImpl(unit_of_work.session), Argon2PasswordHasher())
    await accounts.create_first_system_admin(SYSTEM_ADMIN_EMAIL, FIRST_PASSWORD)


@pytest.fixture
async def customer_id(unit_of_work) -> int:
    """A customer who already chose their password with the access code of a store."""
    users = UserRepositoryImpl(unit_of_work.session)
    user = await users.find_by_id(await IamFacade(unit_of_work).create_customer_user(CUSTOMER_DNI))
    assert user is not None and user.id is not None
    user.change_password(await Argon2PasswordHasher().hash(CUSTOMER_PASSWORD))
    await users.update(user)
    customer = Customer(Dni(CUSTOMER_DNI), user.id)
    await CustomerRepositoryImpl(unit_of_work.session).add(customer)
    assert customer.id is not None
    return customer.id


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


async def test_an_ip_that_used_all_its_attempts_cannot_sign_in_even_with_the_password(
    client, store_admin_id
):
    for _ in range(MAXIMUM_ATTEMPTS):
        wrong = await login(client, ADMIN_EMAIL, "otra-clave")

    right = await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

    assert wrong.status_code == 401
    assert (right.status_code, right.json()["code"]) == (429, "TOO_MANY_ATTEMPTS")


async def test_system_admin_is_blocked_until_changing_the_first_password(client, system_admin):
    signed_in = await login(client, SYSTEM_ADMIN_EMAIL, FIRST_PASSWORD)
    blocked = await client.get("/api/v1/bcrp-caps/current", headers=bearer(signed_in))
    me = await client.get("/api/v1/auth/me", headers=bearer(signed_in))
    changed = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": FIRST_PASSWORD, "new_password": "mi-clave-segura"},
        headers=bearer(signed_in),
    )
    unblocked = await client.get("/api/v1/bcrp-caps/current", headers=bearer(changed))

    assert signed_in.json()["must_change_password"] is True
    assert (blocked.status_code, blocked.json()["code"]) == (403, "PASSWORD_CHANGE_REQUIRED")
    assert (me.json()["role"], me.json()["must_change_password"]) == ("SYSTEM_ADMIN", True)
    assert (changed.status_code, changed.json()["must_change_password"]) == (200, False)
    assert unblocked.status_code != 403
    assert (await login(client, SYSTEM_ADMIN_EMAIL, "mi-clave-segura")).status_code == 200


async def test_customer_signs_in_with_the_dni_and_reads_their_profile(client, customer_id):
    signed_in = await login(client, CUSTOMER_DNI, CUSTOMER_PASSWORD)
    me = await client.get("/api/v1/auth/me", headers=bearer(signed_in))

    assert (signed_in.json()["role"], signed_in.json()["must_change_password"]) == (
        "CUSTOMER",
        False,
    )
    assert (me.json()["username"], me.json()["customer_id"]) == (CUSTOMER_DNI, customer_id)


async def test_wrong_current_password_is_reported_on_its_field(client, customer_id):
    signed_in = await login(client, CUSTOMER_DNI, CUSTOMER_PASSWORD)

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
