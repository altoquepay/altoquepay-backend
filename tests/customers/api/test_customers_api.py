"""Tests for the customers endpoints against the migrated PostgreSQL database.

Every test shares one Unit of Work that never commits, so what it creates disappears.
New stores start with cutoff 10, payment 15, TEA 40%, late TEA 15% and 4 weeks.
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app as application
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.shared.interfaces.rest.business_date import get_business_today

PASSWORD = "mi-clave-segura"
NEW_CUSTOMER = {
    "dni": "45678912",
    "first_names": "Rosa",
    "last_names": "Quispe Mamani",
    "phone": "987654321",
    "credit_limit": "1500",
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


async def store_admin(client, ruc: str, email: str) -> dict[str, str]:
    """Register a store through the API and return its signed-in administrator's headers."""
    registered = await client.post(
        "/api/v1/stores/register",
        json={
            "business_name": "Bodega de Prueba",
            "ruc": ruc,
            "full_name": "Admin de Prueba",
            "email": email,
            "password": PASSWORD,
        },
    )
    assert registered.status_code == 201, registered.json()
    signed_in = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {signed_in.json()['access_token']}"}


@pytest.fixture
async def admin(client) -> dict[str, str]:
    return await store_admin(client, "20999999990", "admin@customers-test.pe")


@pytest.fixture
async def other_admin(client) -> dict[str, str]:
    return await store_admin(client, "20999999991", "otro@customers-test.pe")


async def open_account(client, headers, **changes):
    return await client.post("/api/v1/customers", json=NEW_CUSTOMER | changes, headers=headers)


async def test_new_dni_gets_an_account_with_the_store_defaults_and_credentials(client, admin):
    response = await open_account(client, admin)

    assert response.status_code == 201
    body = response.json()
    assert body["account"] | {"id": 0, "customer_id": 0, "created_at": "..."} == {
        "id": 0,
        "customer_id": 0,
        "dni": "45678912",
        "first_names": "Rosa",
        "last_names": "Quispe Mamani",
        "phone": "987654321",
        "address": None,
        "credit_limit": "1500.00",
        "cutoff_day": 10,
        "payment_day": 15,
        "tea": "40.0000000",
        "late_tea": "15.0000000",
        "max_weeks": 4,
        "status": "ACTIVE",
        "created_at": "...",
    }
    credentials = body["credentials"]
    assert credentials["username"] == "45678912"
    signed_in = await client.post(
        "/api/v1/auth/login",
        data={"username": "45678912", "password": credentials["temporary_password"]},
    )
    assert signed_in.json()["must_change_password"] is True


async def test_given_conditions_replace_the_defaults(client, admin):
    response = await open_account(
        client, admin, cutoff_day=20, payment_day=26, tea="75", late_tea="10", max_weeks=8
    )

    account = response.json()["account"]
    assert (account["cutoff_day"], account["payment_day"], account["max_weeks"]) == (20, 26, 8)
    assert (account["tea"], account["late_tea"]) == ("75.0000000", "10.0000000")


async def test_a_given_day_is_checked_against_the_default_ones(client, admin):
    response = await open_account(client, admin, payment_day=5)

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == (
        "PAYMENT_DAY_NOT_AFTER_CUTOFF",
        "payment_day",
    )


@pytest.mark.parametrize(
    ("changes", "field"),
    [({"tea": "114.69"}, "tea"), ({"late_tea": "17.21"}, "late_tea")],
)
async def test_rates_above_the_bcrp_cap_are_rejected(client, admin, changes, field):
    response = await open_account(client, admin, **changes)

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == ("RATE_ABOVE_BCRP_CAP", field)


async def test_repeated_dni_in_the_same_store_is_rejected(client, admin):
    await open_account(client, admin)

    response = await open_account(client, admin)

    assert response.status_code == 409
    assert (response.json()["code"], response.json()["field"]) == (
        "CUSTOMER_ALREADY_IN_STORE",
        "dni",
    )


async def test_new_dni_needs_the_names(client, admin):
    response = await open_account(client, admin, first_names=None)

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == ("INVALID_NAME", "first_names")


async def test_person_from_another_store_keeps_their_user(client, admin, other_admin):
    first = await open_account(client, admin)

    lookup = await client.get("/api/v1/customers/lookup?dni=45678912", headers=other_admin)
    second = await open_account(client, other_admin, first_names=None, last_names=None)

    assert lookup.status_code == 200
    assert lookup.json() | {"customer_id": 0} == {
        "customer_id": 0,
        "dni": "45678912",
        "first_names": "Rosa",
        "last_names": "Quispe Mamani",
        "phone": "987654321",
        "address": None,
        "account_id": None,
        "notice": "PERSON_HAS_ACCOUNT",
    }
    assert second.status_code == 201
    assert second.json()["credentials"] is None
    assert second.json()["account"]["customer_id"] == first.json()["account"]["customer_id"]


async def test_lookup_in_the_own_store_returns_the_account(client, admin):
    opened = await open_account(client, admin)

    lookup = await client.get("/api/v1/customers/lookup?dni=45678912", headers=admin)

    assert (lookup.json()["account_id"], lookup.json()["notice"]) == (
        opened.json()["account"]["id"],
        None,
    )


async def test_unknown_dni_is_not_found(client, admin):
    response = await client.get("/api/v1/customers/lookup?dni=11111111", headers=admin)

    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


async def test_list_filters_by_search_and_status(client, admin):
    rosa = (await open_account(client, admin)).json()["account"]
    await open_account(client, admin, dni="70000002", first_names="Luis", last_names="Torres")
    await client.patch(f"/api/v1/customers/{rosa['id']}/deactivate", headers=admin)

    by_name = await client.get("/api/v1/customers?search=quispe", headers=admin)
    by_dni = await client.get("/api/v1/customers?search=7000", headers=admin)
    active = await client.get("/api/v1/customers?status=ACTIVE", headers=admin)

    assert [item["dni"] for item in by_name.json()["items"]] == ["45678912"]
    assert [item["dni"] for item in by_dni.json()["items"]] == ["70000002"]
    assert (active.json()["total"], active.json()["items"][0]["dni"]) == (1, "70000002")


async def test_update_replaces_data_and_terms(client, admin):
    account_id = (await open_account(client, admin)).json()["account"]["id"]
    changes = {
        "first_names": "Rosa María",
        "last_names": "Quispe Mamani",
        "phone": None,
        "address": "Jr. Los Pinos 456",
        "credit_limit": "2000",
        "cutoff_day": 20,
        "payment_day": 26,
        "tea": "75",
        "late_tea": "10",
        "max_weeks": 8,
    }

    response = await client.put(f"/api/v1/customers/{account_id}", json=changes, headers=admin)
    stored = await client.get(f"/api/v1/customers/{account_id}", headers=admin)

    assert response.status_code == 200
    assert stored.json() == response.json()
    assert (stored.json()["first_names"], stored.json()["phone"]) == ("Rosa María", None)
    assert (stored.json()["credit_limit"], stored.json()["tea"]) == ("2000.00", "75.0000000")


async def test_deactivated_account_stays_listed_as_inactive(client, admin):
    account_id = (await open_account(client, admin)).json()["account"]["id"]

    response = await client.patch(f"/api/v1/customers/{account_id}/deactivate", headers=admin)

    assert response.json()["status"] == "INACTIVE"


async def test_reset_password_gives_a_new_temporary_password(client, admin):
    account_id = (await open_account(client, admin)).json()["account"]["id"]

    response = await client.post(f"/api/v1/customers/{account_id}/reset-password", headers=admin)
    signed_in = await client.post(
        "/api/v1/auth/login",
        data={"username": "45678912", "password": response.json()["temporary_password"]},
    )

    assert response.json()["username"] == "45678912"
    assert signed_in.json()["must_change_password"] is True


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "", None),
        ("PUT", "", {"first_names": "x"}),
        ("PATCH", "/deactivate", None),
        ("POST", "/reset-password", None),
    ],
)
async def test_account_of_another_store_is_not_found(
    client, admin, other_admin, method, path, body
):
    account_id = (await open_account(client, admin)).json()["account"]["id"]
    full_body = None
    if body is not None:
        full_body = {
            "first_names": "x",
            "last_names": "y",
            "credit_limit": "1",
            "cutoff_day": 10,
            "payment_day": 15,
            "tea": "40",
            "late_tea": "15",
            "max_weeks": 4,
        }

    response = await client.request(
        method, f"/api/v1/customers/{account_id}{path}", json=full_body, headers=other_admin
    )

    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


async def test_only_store_admins_reach_the_customers(client):
    response = await client.get("/api/v1/customers")

    assert response.status_code == 401
