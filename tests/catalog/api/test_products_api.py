"""Tests for the products endpoints against the migrated PostgreSQL database.

Every test shares one Unit of Work that never commits, images included.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.catalog.infrastructure.persistence.models import ProductImageModel
from app.catalog.interfaces.acl.catalog_facade import CatalogFacade
from app.main import app as application
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work

PASSWORD = "mi-clave-segura"
RICE = {
    "code": "ARR-5",
    "description": "Arroz extra 5 kg",
    "brand": "Costeño",
    "category": "Abarrotes",
    "unit": "bolsa",
    "cash_price": "21.5",
    "list_price": "23.9",
}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


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
    return await store_admin(client, "20999999990", "admin@products-test.pe")


@pytest.fixture
async def other_admin(client) -> dict[str, str]:
    return await store_admin(client, "20999999991", "otro@products-test.pe")


async def create(client, headers, **changes):
    return await client.post("/api/v1/products", json=RICE | changes, headers=headers)


async def test_created_product_has_prices_with_2_decimals(client, admin):
    response = await create(client, admin)

    assert response.status_code == 201
    assert response.json() | {"id": 0} == {
        "id": 0,
        "code": "ARR-5",
        "description": "Arroz extra 5 kg",
        "brand": "Costeño",
        "category": "Abarrotes",
        "unit": "bolsa",
        "supplier": None,
        "cash_price": "21.50",
        "list_price": "23.90",
        "image_url": None,
        "is_active": True,
    }


async def test_repeated_code_in_the_same_store_is_rejected(client, admin, other_admin):
    await create(client, admin)

    repeated = await create(client, admin, description="Otro arroz")
    in_other_store = await create(client, other_admin)

    assert repeated.status_code == 409
    assert (repeated.json()["code"], repeated.json()["field"]) == ("PRODUCT_CODE_TAKEN", "code")
    assert in_other_store.status_code == 201


async def test_update_cannot_take_the_code_of_another_product(client, admin):
    await create(client, admin)
    oil = (await create(client, admin, code="ACE-1")).json()

    taken = await client.put(f"/api/v1/products/{oil['id']}", json=RICE, headers=admin)
    kept = await client.put(
        f"/api/v1/products/{oil['id']}",
        json=RICE | {"code": "ACE-1", "list_price": "13"},
        headers=admin,
    )

    assert (taken.status_code, taken.json()["code"]) == (409, "PRODUCT_CODE_TAKEN")
    assert (kept.status_code, kept.json()["list_price"]) == (200, "13.00")


async def test_list_filters_by_search_and_active(client, admin):
    rice = (await create(client, admin)).json()
    await create(client, admin, code="ACE-1", description="Aceite vegetal 1 L")
    await client.patch(f"/api/v1/products/{rice['id']}/deactivate", headers=admin)

    by_description = await client.get("/api/v1/products?search=aceite", headers=admin)
    inactive = await client.get("/api/v1/products?active=false", headers=admin)
    everything = await client.get("/api/v1/products", headers=admin)

    assert [item["code"] for item in by_description.json()["items"]] == ["ACE-1"]
    assert [item["code"] for item in inactive.json()["items"]] == ["ARR-5"]
    assert [item["code"] for item in everything.json()["items"]] == ["ACE-1", "ARR-5"]


async def test_deactivated_product_cannot_be_sold(client, admin, unit_of_work):
    rice = (await create(client, admin)).json()

    response = await client.patch(f"/api/v1/products/{rice['id']}/deactivate", headers=admin)

    assert response.json()["is_active"] is False
    store_id = await store_of(client, admin)
    with pytest.raises(BusinessError) as error:
        await CatalogFacade(unit_of_work).get_active_products(store_id, [rice["id"]])
    assert error.value.code == "PRODUCT_NOT_AVAILABLE"


async def saved_images(unit_of_work, product_id: int) -> list[str]:
    """Return the names of the stored images of a product."""
    names = await unit_of_work.session.scalars(
        select(ProductImageModel.name).where(ProductImageModel.name.like(f"%/{product_id}-%"))
    )
    return list(names)


async def store_of(client, headers) -> int:
    return (await client.get("/api/v1/store/profile", headers=headers)).json()["id"]


async def test_uploaded_image_is_served_and_replaces_the_previous_one(client, admin, unit_of_work):
    rice = (await create(client, admin)).json()
    url = f"/api/v1/products/{rice['id']}/image"

    first = await client.post(url, files={"image": ("arroz.png", PNG, "image/png")}, headers=admin)
    second = await client.post(url, files={"image": ("arroz.png", PNG, "image/png")}, headers=admin)
    first_url, second_url = first.json()["image_url"], second.json()["image_url"]
    # No sign-in: the browser loads it from an <img> tag.
    served = await client.get(second_url)
    replaced = await client.get(first_url)

    assert second.status_code == 200
    assert second_url.startswith("/media/products/") and second_url.endswith(".png")
    assert second_url != first_url
    assert (served.status_code, served.content) == (200, PNG)
    assert served.headers["content-type"] == "image/png"
    assert served.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert (replaced.status_code, replaced.json()["code"]) == (404, "NOT_FOUND")
    assert await saved_images(unit_of_work, rice["id"]) == [
        second_url.removeprefix("/media/products/")
    ]


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"GIF89a" + b"\x00" * 10, "UNSUPPORTED_IMAGE_TYPE"),
        (PNG + b"\x00" * 2_100_000, "IMAGE_TOO_LARGE"),
    ],
    ids=["not an image", "over 2 MB"],
)
async def test_invalid_image_is_rejected_and_not_saved(client, admin, unit_of_work, content, code):
    rice = (await create(client, admin)).json()

    response = await client.post(
        f"/api/v1/products/{rice['id']}/image",
        files={"image": ("foto.png", content, "image/png")},
        headers=admin,
    )

    assert response.status_code == 422
    assert (response.json()["code"], response.json()["field"]) == (code, "image")
    assert await saved_images(unit_of_work, rice["id"]) == []


@pytest.mark.parametrize(
    ("method", "path", "send"),
    [("GET", "", {}), ("PUT", "", {"json": RICE}), ("PATCH", "/deactivate", {})],
)
async def test_product_of_another_store_is_not_found(
    client, admin, other_admin, method, path, send
):
    rice = (await create(client, admin)).json()

    response = await client.request(
        method, f"/api/v1/products/{rice['id']}{path}", headers=other_admin, **send
    )

    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


async def test_image_of_another_store_product_is_not_found(
    client, admin, other_admin, unit_of_work
):
    rice = (await create(client, admin)).json()

    response = await client.post(
        f"/api/v1/products/{rice['id']}/image",
        files={"image": ("arroz.png", PNG, "image/png")},
        headers=other_admin,
    )

    assert response.status_code == 404
    assert await saved_images(unit_of_work, rice["id"]) == []


async def test_unknown_image_is_not_found(client):
    response = await client.get("/media/products/1/1-0000000000000000.png")

    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")
