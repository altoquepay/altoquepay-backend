"""Tests for the stores endpoints against the migrated PostgreSQL database.

Every test shares one Unit of Work that never commits, so the stores it creates disappear.
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app as application
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.shared.interfaces.rest.business_date import get_business_today
from tests.authorization import authorization

REGISTRATION = {
    "business_name": "Bodega La Esquina",
    "ruc": "10456781234",
    "full_name": "Rosa Quispe",
    "email": "rosa@bodega-stores-test.pe",
    "password": "mi-clave-segura",
}


class RollbackUnitOfWork(UnitOfWork):
    async def commit(self) -> None:
        await self.session.flush()


@pytest.fixture
async def client():
    async with RollbackUnitOfWork(session_factory) as unit_of_work:
        application.dependency_overrides[get_unit_of_work] = lambda: unit_of_work
        application.dependency_overrides[get_business_today] = lambda: date(2026, 11, 12)
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        application.dependency_overrides.clear()


async def register(client, **overrides):
    return await client.post("/api/v1/stores/register", json=REGISTRATION | overrides)


async def login(client, email: str = REGISTRATION["email"]):
    return await client.post(
        "/api/v1/auth/login", data={"username": email, "password": REGISTRATION["password"]}
    )


async def registered_admin(client, **overrides) -> dict[str, str]:
    """Register a store and return the headers of its signed-in administrator."""
    await register(client, **overrides)
    signed_in = await login(client, overrides.get("email", REGISTRATION["email"]))
    return {"Authorization": f"Bearer {signed_in.json()['access_token']}"}


PROFILE = {
    "business_name": "Bodega Don Lucho",
    "address": "Av. Los Jardines 123, SJL",
    "phone": "987654321",
    "default_cutoff_day": 20,
    "default_payment_day": 26,
    "default_tea": "114.68",
    "default_late_tea": "17.202",
    "default_max_weeks": 8,
}


async def test_registered_store_starts_with_the_initial_conditions(client):
    response = await register(client)

    assert response.status_code == 201
    body = response.json()
    assert body | {"id": 0, "registered_at": "..."} == {
        "id": 0,
        "business_name": "Bodega La Esquina",
        "ruc": "10456781234",
        "address": None,
        "phone": None,
        "status": "ACTIVE",
        "registered_at": "...",
        "default_cutoff_day": 10,
        "default_payment_day": 15,
        "default_tea": "40.0000000",
        "default_late_tea": "15.0000000",
        "default_max_weeks": 4,
    }


async def test_administrator_of_a_registered_store_can_sign_in(client):
    await register(client)

    signed_in = await login(client)

    assert signed_in.status_code == 200
    assert signed_in.json()["role"] == "STORE_ADMIN"


@pytest.mark.parametrize(
    ("invalid_values", "status", "code", "field"),
    [
        ({"ruc": "1045678123"}, 422, "INVALID_RUC", "ruc"),
        ({"business_name": "  "}, 422, "INVALID_BUSINESS_NAME", "business_name"),
        ({"password": "corta"}, 422, "INVALID_PASSWORD", "password"),
        ({"email": "no-es-correo"}, 422, "INVALID_EMAIL", "email"),
    ],
)
async def test_invalid_registration_is_rejected_on_its_field(
    client, invalid_values, status, code, field
):
    response = await register(client, **invalid_values)

    assert response.status_code == status
    assert (response.json()["code"], response.json()["field"]) == (code, field)


async def test_repeated_ruc_or_email_is_rejected(client):
    await register(client)

    repeated_ruc = await register(client, email="otra@bodega-stores-test.pe")
    repeated_email = await register(client, ruc="10456781235")

    assert (repeated_ruc.status_code, repeated_ruc.json()["code"]) == (409, "RUC_TAKEN")
    assert (repeated_email.status_code, repeated_email.json()["code"]) == (409, "EMAIL_TAKEN")


async def test_administrator_reads_and_updates_their_store_profile(client):
    admin = await registered_admin(client)

    updated = await client.put("/api/v1/store/profile", json=PROFILE, headers=admin)
    profile = await client.get("/api/v1/store/profile", headers=admin)

    assert updated.status_code == 200
    assert profile.json() == updated.json()
    assert profile.json()["ruc"] == REGISTRATION["ruc"]
    assert {key: profile.json()[key] for key in PROFILE} == PROFILE | {
        "default_tea": "114.6800000",
        "default_late_tea": "17.2020000",
    }


async def test_each_administrator_sees_only_their_own_store(client):
    first = await registered_admin(client)
    second = await registered_admin(client, ruc="10456781235", email="otra@bodega-stores-test.pe")

    first_profile = await client.get("/api/v1/store/profile", headers=first)
    second_profile = await client.get("/api/v1/store/profile", headers=second)

    assert first_profile.json()["ruc"] == "10456781234"
    assert second_profile.json()["ruc"] == "10456781235"


@pytest.mark.parametrize(
    ("invalid_values", "code", "field"),
    [
        ({"default_cutoff_day": 26}, "INVALID_DAY_RANGE", "default_cutoff_day"),
        ({"default_payment_day": 29}, "INVALID_DAY_RANGE", "default_payment_day"),
        ({"default_payment_day": 20}, "PAYMENT_DAY_NOT_AFTER_CUTOFF", "default_payment_day"),
        ({"default_max_weeks": 100}, "INVALID_MAX_WEEKS", "default_max_weeks"),
        ({"default_tea": "114.69"}, "RATE_ABOVE_BCRP_CAP", "default_tea"),
        ({"default_late_tea": "17.21"}, "RATE_ABOVE_BCRP_CAP", "default_late_tea"),
        ({"default_tea": "-1"}, "VALIDATION_ERROR", "default_tea"),
    ],
)
async def test_invalid_profile_is_rejected_on_its_field(client, invalid_values, code, field):
    admin = await registered_admin(client)

    response = await client.put(
        "/api/v1/store/profile", json=PROFILE | invalid_values, headers=admin
    )

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == (code, field)


async def test_profile_needs_the_administrator_of_a_store(client):
    system_admin = authorization(sub="1", role="SYSTEM_ADMIN", store_id=None)

    assert (await client.get("/api/v1/store/profile")).status_code == 401
    assert (await client.get("/api/v1/store/profile", headers=system_admin)).status_code == 403


SYSTEM_ADMIN = authorization(sub="1", role="SYSTEM_ADMIN", store_id=None)


async def test_system_admin_lists_stores_newest_first_with_their_customers(client):
    await register(client)
    await register(client, ruc="10456781235", email="otra@bodega-stores-test.pe")

    response = await client.get("/api/v1/admin/stores?page=1&size=2", headers=SYSTEM_ADMIN)

    assert response.status_code == 200
    page = response.json()
    assert page["total"] >= 2
    assert [store["ruc"] for store in page["items"]] == ["10456781235", "10456781234"]
    assert page["items"][0]["customers_count"] == 0


async def test_system_admin_deactivates_and_reactivates_a_store(client):
    store_id = (await register(client)).json()["id"]

    deactivated = await client.patch(
        f"/api/v1/admin/stores/{store_id}/deactivate", headers=SYSTEM_ADMIN
    )
    reactivated = await client.patch(
        f"/api/v1/admin/stores/{store_id}/reactivate", headers=SYSTEM_ADMIN
    )

    assert (deactivated.status_code, deactivated.json()["status"]) == (200, "INACTIVE")
    assert (reactivated.status_code, reactivated.json()["status"]) == (200, "ACTIVE")


async def test_unknown_store_cannot_be_deactivated(client):
    response = await client.patch("/api/v1/admin/stores/999999/deactivate", headers=SYSTEM_ADMIN)

    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


async def test_store_administrator_cannot_manage_stores(client):
    admin = await registered_admin(client)

    assert (await client.get("/api/v1/admin/stores", headers=admin)).status_code == 403
    assert (
        await client.patch("/api/v1/admin/stores/1/deactivate", headers=admin)
    ).status_code == 403


async def test_deactivated_store_is_blocked_at_once_until_reactivated(client):
    admin = await registered_admin(client)
    store_id = (await client.get("/api/v1/store/profile", headers=admin)).json()["id"]

    await client.patch(f"/api/v1/admin/stores/{store_id}/deactivate", headers=SYSTEM_ADMIN)
    blocked_login = await login(client)
    blocked_profile = await client.get("/api/v1/store/profile", headers=admin)
    await client.patch(f"/api/v1/admin/stores/{store_id}/reactivate", headers=SYSTEM_ADMIN)

    assert (blocked_login.status_code, blocked_login.json()["code"]) == (403, "STORE_INACTIVE")
    assert (blocked_profile.status_code, blocked_profile.json()["code"]) == (403, "STORE_INACTIVE")
    assert (await login(client)).status_code == 200
    assert (await client.get("/api/v1/store/profile", headers=admin)).status_code == 200
