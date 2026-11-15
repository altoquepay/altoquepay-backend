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
