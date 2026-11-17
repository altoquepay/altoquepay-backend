"""Tests for the customers endpoints against the migrated PostgreSQL database.

Every test shares one Unit of Work that never commits, so what it creates disappears.
New stores start with cutoff 10, payment 15, TEA 40%, late TEA 15% and 4 weeks.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app as application
from app.shared.infrastructure.unit_of_work import get_unit_of_work
from app.shared.interfaces.rest.business_date import get_business_now, get_business_today

PASSWORD = "mi-clave-segura"
NEW_CUSTOMER = {
    "dni": "45678912",
    "first_names": "Rosa",
    "last_names": "Quispe Mamani",
    "phone": "987654321",
    "credit_limit": "1500",
}


@pytest.fixture
async def client(unit_of_work):
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


async def redeem(client, code: str, dni: str = "45678912", password: str = PASSWORD):
    """Redeem a store's access code without a session, choosing a password."""
    return await client.post(
        "/api/v1/auth/redeem-access-code",
        json={"dni": dni, "code": code, "new_password": password},
    )


async def sign_in(client, dni: str = "45678912", password: str = PASSWORD):
    return await client.post("/api/v1/auth/login", data={"username": dni, "password": password})


async def test_new_dni_gets_an_account_with_the_store_defaults_and_an_access_code(client, admin):
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
        "portal_linked": False,
        "created_at": "...",
    }
    access_code = body["access_code"]
    expires_in = datetime.fromisoformat(access_code["expires_at"]) - datetime.now(UTC)
    assert len(access_code["code"]) == 12
    assert timedelta(hours=47) < expires_in <= timedelta(hours=48)


async def test_the_code_lets_the_customer_choose_a_password_and_links_the_store(client, admin):
    opened = (await open_account(client, admin)).json()
    code = opened["access_code"]["code"]

    # Typed by hand: lowercase and a hyphen in the middle are still the same code.
    redeemed = await redeem(client, f"{code[:5]}-{code[5:]}".lower())
    signed_in = await sign_in(client)
    account = await client.get(f"/api/v1/customers/{opened['account']['id']}", headers=admin)

    assert redeemed.status_code == 204
    assert (signed_in.status_code, signed_in.json()["must_change_password"]) == (200, False)
    assert account.json()["portal_linked"] is True


async def test_a_code_needs_its_own_dni_and_works_only_once(client, admin):
    code = (await open_account(client, admin)).json()["access_code"]["code"]
    await open_account(client, admin, dni="70000002", first_names="Luis", last_names="Torres")

    of_another_person = await redeem(client, code, dni="70000002")
    of_nobody = await redeem(client, code, dni="11111111")
    made_up = await redeem(client, "AAAAAAAAAA")
    short_password = await redeem(client, code, password="corta")
    first_use = await redeem(client, code)
    second_use = await redeem(client, code, password="otra-clave-segura")

    for refused in (of_another_person, of_nobody, made_up, second_use):
        assert (refused.status_code, refused.json()["code"], refused.json()["field"]) == (
            422,
            "INVALID_ACCESS_CODE",
            "code",
        )
    assert (short_password.json()["code"], short_password.json()["field"]) == (
        "INVALID_PASSWORD",
        "new_password",
    )
    assert first_use.status_code == 204
    assert (await sign_in(client, password="otra-clave-segura")).status_code == 401


async def test_an_expired_or_replaced_code_is_refused(client, admin):
    opened = (await open_account(client, admin)).json()
    old_code = opened["access_code"]["code"]
    reissued = await client.post(
        f"/api/v1/customers/{opened['account']['id']}/access-code", headers=admin
    )
    new_code = reissued.json()["code"]

    replaced = await redeem(client, old_code)
    application.dependency_overrides[get_business_now] = lambda: (
        datetime.now(UTC) + timedelta(hours=49)
    )
    expired = await redeem(client, new_code)

    assert (reissued.status_code, new_code != old_code) == (200, True)
    for refused in (replaced, expired):
        assert (refused.status_code, refused.json()["code"]) == (422, "INVALID_ACCESS_CODE")
    assert (await sign_in(client)).status_code == 401


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


async def test_an_account_needs_the_names(client, admin):
    response = await open_account(client, admin, first_names="  ")

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == ("INVALID_NAME", "first_names")


async def test_person_from_another_store_keeps_their_user_and_gets_a_code(
    client, admin, other_admin
):
    first = await open_account(client, admin)

    lookup = await client.get("/api/v1/customers/lookup?dni=45678912", headers=other_admin)
    without_names = await open_account(client, other_admin, first_names=None, last_names=None)
    second = await open_account(client, other_admin, first_names="Rosa María", phone=None)

    assert lookup.status_code == 200
    # Nothing the first store typed about the person reaches the second one.
    assert lookup.json() | {"customer_id": 0} == {
        "customer_id": 0,
        "dni": "45678912",
        "account_id": None,
        "notice": "PERSON_HAS_ACCOUNT",
    }
    assert (without_names.status_code, without_names.json()["field"]) == (422, "first_names")
    assert second.status_code == 201
    assert (second.json()["account"]["first_names"], second.json()["account"]["phone"]) == (
        "Rosa María",
        None,
    )
    assert second.json()["access_code"]["code"] != first.json()["access_code"]["code"]
    assert second.json()["account"]["portal_linked"] is False
    assert second.json()["account"]["customer_id"] == first.json()["account"]["customer_id"]


async def test_a_code_redeemed_without_a_session_leaves_only_its_store_linked(
    client, admin, other_admin
):
    first = (await open_account(client, admin)).json()
    await redeem(client, first["access_code"]["code"])
    second = (await open_account(client, other_admin)).json()
    second_path = f"/api/v1/customers/{second['account']['id']}"

    async def linked() -> tuple[bool, bool]:
        """Whether each store sees its account in the customer's portal."""
        in_first = await client.get(f"/api/v1/customers/{first['account']['id']}", headers=admin)
        in_second = await client.get(second_path, headers=other_admin)
        return in_first.json()["portal_linked"], in_second.json()["portal_linked"]

    after_opening = await linked()
    session = {"Authorization": f"Bearer {(await sign_in(client)).json()['access_token']}"}
    added = await client.post(
        "/api/v1/me/stores/link", json={"code": second["access_code"]["code"]}, headers=session
    )
    after_adding = await linked()
    still_signed_in = await client.get("/api/v1/me/stores", headers=session)
    # The customer forgets the password and recovers it with a new code of the second store.
    new_code = (await client.post(f"{second_path}/access-code", headers=other_admin)).json()
    recovered = await redeem(client, new_code["code"], password="otra-clave-segura")
    after_recovering = await linked()
    # Whoever knew the previous password keeps a token: it must stop working at once.
    old_session = await client.get("/api/v1/me/stores", headers=session)
    old_session_link = await client.post(
        "/api/v1/me/stores/link", json={"code": "AAAAAAAAAA"}, headers=session
    )
    new_sign_in = await sign_in(client, password="otra-clave-segura")
    new_session = await client.get(
        "/api/v1/me/stores",
        headers={"Authorization": f"Bearer {new_sign_in.json()['access_token']}"},
    )

    assert after_opening == (True, False)
    assert (added.status_code, after_adding) == (204, (True, True))
    assert still_signed_in.status_code == 200
    assert (recovered.status_code, after_recovering) == (204, (False, True))
    assert (old_session.status_code, old_session_link.status_code) == (401, 401)
    assert (await sign_in(client)).status_code == 401
    assert (new_sign_in.status_code, new_session.status_code) == (200, 200)


async def test_a_store_that_opens_an_account_for_an_active_customer_cannot_take_over(
    client, admin, other_admin
):
    first = (await open_account(client, admin)).json()
    await redeem(client, first["access_code"]["code"])
    # Another store opens an account for the same DNI without the customer and redeems its code.
    second = (await open_account(client, other_admin)).json()

    taken = await redeem(client, second["access_code"]["code"], password="clave-de-la-tienda")

    assert (taken.status_code, taken.json()["code"]) == (403, "STORE_NOT_TRUSTED")
    assert (await sign_in(client)).status_code == 200
    assert (await sign_in(client, password="clave-de-la-tienda")).status_code == 401


async def test_support_chooses_the_only_store_that_may_restore_the_access(
    client, admin, other_admin, stored_system_admin
):
    # A store activated the customer's DNI before them; the customer's own store is refused.
    first = (await open_account(client, admin)).json()
    await redeem(client, first["access_code"]["code"], password="clave-de-la-tienda")
    own = (await open_account(client, other_admin)).json()
    refused = await redeem(client, own["access_code"]["code"])
    own_store_id = (await client.get("/api/v1/store/profile", headers=other_admin)).json()["id"]
    support = stored_system_admin

    def trust(store_id: int, headers: dict[str, str]):
        return client.post(
            "/api/v1/admin/customers/trusted-store",
            json={"dni": "45678912", "store_id": store_id},
            headers=headers,
        )

    as_store = await trust(own_store_id, admin)
    without_account = await trust(999_999, support)
    trusted = await trust(own_store_id, support)
    restored = await redeem(client, own["access_code"]["code"])
    first_path = f"/api/v1/customers/{first['account']['id']}"
    new_code = (await client.post(f"{first_path}/access-code", headers=admin)).json()["code"]
    taken_again = await redeem(client, new_code, password="clave-de-la-tienda")

    assert refused.json()["code"] == "STORE_NOT_TRUSTED"
    assert (as_store.status_code, without_account.status_code) == (403, 404)
    assert (trusted.status_code, restored.status_code) == (204, 204)
    assert (await client.get(first_path, headers=admin)).json()["portal_linked"] is False
    assert (taken_again.status_code, taken_again.json()["code"]) == (403, "STORE_NOT_TRUSTED")
    assert (await sign_in(client)).status_code == 200


async def test_a_deactivated_store_cannot_use_the_codes_it_issued_before(
    client, admin, stored_system_admin
):
    opened = (await open_account(client, admin)).json()
    store_id = (await client.get("/api/v1/store/profile", headers=admin)).json()["id"]
    support = stored_system_admin

    await client.patch(f"/api/v1/admin/stores/{store_id}/deactivate", headers=support)
    refused = await redeem(client, opened["access_code"]["code"])
    await client.patch(f"/api/v1/admin/stores/{store_id}/reactivate", headers=support)
    after_reactivating = await redeem(client, opened["access_code"]["code"])

    assert (refused.status_code, refused.json()["code"]) == (403, "STORE_INACTIVE")
    assert after_reactivating.status_code == 204


async def test_only_the_customer_of_the_code_adds_the_store(client, admin):
    rosa = (await open_account(client, admin)).json()
    await redeem(client, rosa["access_code"]["code"])
    luis = (
        await open_account(client, admin, dni="70000002", first_names="Luis", last_names="Torres")
    ).json()
    link = {"code": luis["access_code"]["code"]}
    as_rosa = {"Authorization": f"Bearer {(await sign_in(client)).json()['access_token']}"}

    stolen = await client.post("/api/v1/me/stores/link", json=link, headers=as_rosa)
    as_store = await client.post("/api/v1/me/stores/link", json=link, headers=admin)
    without_token = await client.post("/api/v1/me/stores/link", json=link)

    assert (stolen.status_code, stolen.json()["code"]) == (422, "INVALID_ACCESS_CODE")
    assert (as_store.status_code, without_token.status_code) == (403, 401)
    assert (await redeem(client, luis["access_code"]["code"], dni="70000002")).status_code == 204


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


async def test_what_a_store_edits_never_changes_the_account_of_another_store(
    client, admin, other_admin
):
    first = (await open_account(client, admin, address="Jr. Las Flores 123")).json()["account"]
    second = (await open_account(client, other_admin)).json()["account"]
    changes = {
        "first_names": "Otro",
        "last_names": "Nombre",
        "phone": "900000000",
        "address": "Otra dirección",
        "credit_limit": "1",
        "cutoff_day": 10,
        "payment_day": 15,
        "tea": "40",
        "late_tea": "15",
        "max_weeks": 4,
    }

    changed = await client.put(
        f"/api/v1/customers/{second['id']}", json=changes, headers=other_admin
    )
    seen_by_first = (await client.get(f"/api/v1/customers/{first['id']}", headers=admin)).json()

    assert changed.status_code == 200
    person_fields = ("first_names", "last_names", "phone", "address")
    assert [seen_by_first[field] for field in person_fields] == [
        "Rosa",
        "Quispe Mamani",
        "987654321",
        "Jr. Las Flores 123",
    ]


async def test_deactivated_account_stays_listed_as_inactive(client, admin):
    account_id = (await open_account(client, admin)).json()["account"]["id"]

    response = await client.patch(f"/api/v1/customers/{account_id}/deactivate", headers=admin)

    assert response.json()["status"] == "INACTIVE"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "", None),
        ("PUT", "", {"first_names": "x"}),
        ("PATCH", "/deactivate", None),
        ("POST", "/access-code", None),
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
