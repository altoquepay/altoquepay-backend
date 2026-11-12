"""Tests for the BCRP cap endpoints against the migrated PostgreSQL database.

Every test shares one Unit of Work that never commits, so the seeded caps stay as they are.
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.iam.domain.model.aggregates.user import User
from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.main import app as application
from app.regulation.interfaces.rest.dependencies import get_business_today
from app.shared.domain.value_objects import Role
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from tests.authorization import authorization

SYSTEM_ADMIN = authorization(sub="1", role="SYSTEM_ADMIN", store_id=None)
CUSTOMER = authorization(sub="9", role="CUSTOMER", store_id=None, customer_id=4)
NEXT_CAP = {"max_tea": "110.5", "valid_from": "2027-05-01", "valid_to": "2027-10-31"}


class RollbackUnitOfWork(UnitOfWork):
    async def commit(self) -> None:
        await self.session.flush()


@pytest.fixture
async def unit_of_work():
    async with RollbackUnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture
async def client(unit_of_work):
    application.dependency_overrides[get_unit_of_work] = lambda: unit_of_work
    application.dependency_overrides[get_business_today] = lambda: date(2026, 11, 12)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    application.dependency_overrides.clear()


@pytest.fixture
async def stored_system_admin(unit_of_work) -> dict[str, str]:
    """Headers of a system admin that exists, since bcrp_caps.created_by references users."""
    admin = User("admin@bcrp-test.pe", "unused-hash", Role.SYSTEM_ADMIN)
    await UserRepositoryImpl(unit_of_work.session).add(admin)
    return authorization(sub=str(admin.id), role="SYSTEM_ADMIN", store_id=None)


async def test_any_signed_in_user_gets_the_cap_in_force(client):
    response = await client.get("/api/v1/bcrp-caps/current", headers=CUSTOMER)

    assert response.status_code == 200
    assert response.json() == {
        "id": response.json()["id"],
        "max_tea": "114.6800000",
        "max_late_tea": "17.2020000",
        "valid_from": "2026-11-01",
        "valid_to": "2027-04-30",
    }


async def test_current_cap_requires_a_token(client):
    assert (await client.get("/api/v1/bcrp-caps/current")).status_code == 401


async def test_missing_cap_in_force_is_reported(client):
    application.dependency_overrides[get_business_today] = lambda: date(2027, 5, 1)

    response = await client.get("/api/v1/bcrp-caps/current", headers=CUSTOMER)

    assert response.status_code == 409
    assert response.json()["code"] == "NO_BCRP_CAP_IN_FORCE"


async def test_admin_registers_the_next_cap_and_sees_it_first_in_the_history(
    client, stored_system_admin
):
    registered = await client.post(
        "/api/v1/admin/bcrp-caps", json=NEXT_CAP, headers=stored_system_admin
    )
    history = await client.get("/api/v1/admin/bcrp-caps", headers=stored_system_admin)

    assert registered.status_code == 201
    assert registered.json()["max_tea"] == "110.5000000"
    assert registered.json()["max_late_tea"] == "16.5750000"
    assert history.json()[0] == registered.json()


async def test_overlapping_cap_is_rejected(client):
    overlapping = {**NEXT_CAP, "valid_from": "2027-04-30"}

    response = await client.post("/api/v1/admin/bcrp-caps", json=overlapping, headers=SYSTEM_ADMIN)

    assert response.status_code == 409
    assert response.json()["code"] == "BCRP_CAP_OVERLAP"
    assert response.json()["field"] == "valid_from"


@pytest.mark.parametrize(
    ("invalid_cap", "code", "field"),
    [
        ({**NEXT_CAP, "valid_to": "2027-04-30"}, "INVALID_VALIDITY_PERIOD", "valid_to"),
        ({**NEXT_CAP, "max_tea": "0"}, "VALIDATION_ERROR", "max_tea"),
        ({**NEXT_CAP, "max_tea": "110.12345678"}, "VALIDATION_ERROR", "max_tea"),
    ],
)
async def test_invalid_cap_is_rejected(client, invalid_cap, code, field):
    response = await client.post("/api/v1/admin/bcrp-caps", json=invalid_cap, headers=SYSTEM_ADMIN)

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == (code, field)


async def test_store_admin_cannot_manage_caps(client):
    store_admin = authorization()

    listed = await client.get("/api/v1/admin/bcrp-caps", headers=store_admin)
    registered = await client.post("/api/v1/admin/bcrp-caps", json=NEXT_CAP, headers=store_admin)

    assert (listed.status_code, registered.status_code) == (403, 403)
