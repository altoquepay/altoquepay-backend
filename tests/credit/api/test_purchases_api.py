"""Tests for the purchase endpoints, with the real facades of customers, catalog and billing.

Every test shares one Unit of Work that never commits, so what it creates disappears.
"""

from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.customers.domain.model.aggregates.store_customer import AccountStatus
from app.main import app as application
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work
from app.shared.interfaces.rest.business_date import get_business_now
from tests.authorization import authorization
from tests.credit.stored_credit import LIMA, add_credit_setup
from tests.stored_account import add_account, add_customer

NOW = datetime(2026, 11, 16, 10, tzinfo=LIMA)


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
    application.dependency_overrides[get_business_now] = lambda: NOW
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    application.dependency_overrides.clear()


@pytest.fixture
async def setup(unit_of_work):
    """A store with a S/ 100 product and an account: TEA 75%, cutoff 14, payment 26, limit 1500."""
    return await add_credit_setup(unit_of_work)


@pytest.fixture
def admin(setup):
    return authorization(sub=str(setup.user_id), store_id=setup.store_id)


def report_test_3(setup, **overrides):
    """S/ 400 on 15/10/2026 after the cutoff of the 14th, in 4 weekly installments."""
    return {
        "customer_id": setup.account_id,
        "purchased_at": "2026-10-15T12:00:00-05:00",
        "mode": "WEEKLY",
        "installments_count": 4,
        "items": [{"product_id": setup.product_id, "quantity": 4}],
    } | overrides


async def test_weekly_purchase_follows_report_test_3(client, setup, admin):
    response = await client.post("/api/v1/purchases", json=report_test_3(setup), headers=admin)

    assert response.status_code == 201
    purchase = response.json()
    assert {key: purchase[key] for key in ("amount", "grace_days", "capitalized_amount")} == {
        "amount": "400.00",
        "grace_days": 42,
        "capitalized_amount": "426.99",
    }
    assert (purchase["weekly_rate"], purchase["installment_amount"]) == ("1.0940836", "109.68")
    assert (purchase["ordinary_interest"], purchase["total"]) == ("11.74", "438.73")
    assert purchase["items"] == [
        {
            "product_id": setup.product_id,
            "quantity": 4,
            "unit_list_price": "100.00",
            "subtotal": "400.00",
        }
    ]
    # Today is 16/11/2026, so no installment is overdue yet.
    assert [(i["due_date"], i["amount"], i["status"]) for i in purchase["installments"]] == [
        ("2026-12-03", "109.68", "PENDING"),
        ("2026-12-10", "109.68", "PENDING"),
        ("2026-12-17", "109.68", "PENDING"),
        ("2026-12-24", "109.69", "PENDING"),
    ]


async def test_simulation_calculates_without_saving(client, setup, admin):
    simulated = await client.post(
        "/api/v1/purchases/simulate", json=report_test_3(setup), headers=admin
    )
    # The whole limit is still available, so nothing was saved by the simulation.
    full_limit = await client.post(
        "/api/v1/purchases/simulate",
        json=report_test_3(setup, mode="SINGLE_DATE", installments_count=None)
        | {"items": [{"product_id": setup.product_id, "quantity": 15}]},
        headers=admin,
    )

    assert simulated.status_code == 200
    assert (simulated.json()["id"], simulated.json()["total"]) == (None, "438.73")
    assert full_limit.status_code == 200


async def test_purchase_beyond_the_available_credit_is_rejected(client, setup, admin):
    single_date = report_test_3(setup, mode="SINGLE_DATE", installments_count=None)
    first = await client.post(
        "/api/v1/purchases",
        json=single_date | {"items": [{"product_id": setup.product_id, "quantity": 10}]},
        headers=admin,
    )

    second = await client.post(
        "/api/v1/purchases",
        json=single_date | {"items": [{"product_id": setup.product_id, "quantity": 6}]},
        headers=admin,
    )

    assert first.status_code == 201
    assert (second.status_code, second.json()["code"]) == (422, "CREDIT_LIMIT_EXCEEDED")
    assert second.json()["details"] == {"available": "500.00"}


@pytest.mark.parametrize(
    ("overrides", "status", "code", "field"),
    [
        ({"installments_count": 5}, 422, "MAX_WEEKS_EXCEEDED", "installments_count"),
        ({"purchased_at": "2026-11-16T10:00:01-05:00"}, 422, "PURCHASE_IN_FUTURE", "purchased_at"),
        ({"purchased_at": "2026-10-15T12:00:00"}, 422, "VALIDATION_ERROR", "purchased_at"),
        ({"customer_id": 999999}, 404, "NOT_FOUND", None),
        ({"items": [{"product_id": 999999, "quantity": 1}]}, 422, "PRODUCT_NOT_AVAILABLE", "items"),
    ],
)
async def test_invalid_purchase_is_rejected(client, setup, admin, overrides, status, code, field):
    response = await client.post(
        "/api/v1/purchases", json=report_test_3(setup, **overrides), headers=admin
    )

    assert response.status_code == status
    assert (response.json()["code"], response.json()["field"]) == (code, field)


async def test_customers_and_products_of_other_stores_are_not_found(
    client, unit_of_work, setup, admin
):
    other = await add_credit_setup(unit_of_work, ruc="20999999991", dni="70000002")

    other_customer = await client.post(
        "/api/v1/purchases", json=report_test_3(setup, customer_id=other.account_id), headers=admin
    )
    other_product = await client.post(
        "/api/v1/purchases",
        json=report_test_3(setup, items=[{"product_id": other.product_id, "quantity": 1}]),
        headers=admin,
    )

    assert (other_customer.status_code, other_customer.json()["code"]) == (404, "NOT_FOUND")
    assert other_product.json()["code"] == "PRODUCT_NOT_AVAILABLE"


async def test_inactive_customer_cannot_buy(client, unit_of_work, setup, admin):
    customer = await add_customer(unit_of_work, "70000003")
    inactive = await add_account(
        unit_of_work, setup.store_id, customer.id, 14, 26, AccountStatus.INACTIVE
    )

    response = await client.post(
        "/api/v1/purchases", json=report_test_3(setup, customer_id=inactive.id), headers=admin
    )

    assert (response.status_code, response.json()["code"]) == (409, "ACCOUNT_INACTIVE")


async def test_only_store_administrators_register_purchases(client, setup):
    customer = authorization(role="CUSTOMER", store_id=None, customer_id=1)

    assert (await client.post("/api/v1/purchases", json=report_test_3(setup))).status_code == 401
    response = await client.post("/api/v1/purchases", json=report_test_3(setup), headers=customer)
    assert response.status_code == 403
