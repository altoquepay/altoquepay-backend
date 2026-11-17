"""Tests for the customer portal, the dashboard and the report against the migrated database.

One customer has accounts in two stores. Store A sold them the report's test N°3 both ways on
15/10/2026: S/ 400 in 4 weekly installments (426.99 after grace) and S/ 400 on a single date
(26.99 of interest, cycle of November). Store B sold them S/ 200 on a single date.

Every test shares one Unit of Work that never commits, and sets the day it runs on.
"""

from datetime import date, datetime

import pytest
from httpx import ASGITransport, AsyncClient

import app.billing.interfaces.acl.billing_facade as billing_facade_module
import app.credit.interfaces.acl.credit_facade as credit_facade_module
from app.credit.domain.model.aggregates.purchase import PaymentMode
from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.main import app as application
from app.shared.infrastructure.unit_of_work import get_unit_of_work
from app.shared.interfaces.rest.business_date import get_business_now, get_business_today
from tests.authorization import authorization
from tests.credit.stored_credit import (
    LIMA,
    CreditSetup,
    add_credit_setup,
    add_product,
    add_purchase,
)
from tests.stored_account import add_account
from tests.stored_store import add_store


@pytest.fixture
async def client(unit_of_work):
    application.dependency_overrides[get_unit_of_work] = lambda: unit_of_work
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    application.dependency_overrides.clear()


@pytest.fixture
def on(monkeypatch):
    """Make the API and the facades run on a day in Lima."""

    def set_day(day: date) -> None:
        now = datetime(day.year, day.month, day.day, 12, tzinfo=LIMA)
        application.dependency_overrides[get_business_today] = lambda: day
        application.dependency_overrides[get_business_now] = lambda: now
        for module in (billing_facade_module, credit_facade_module):
            monkeypatch.setattr(module, "get_business_today", lambda: day)
        monkeypatch.setattr(billing_facade_module, "get_business_now", lambda: now)

    return set_day


@pytest.fixture
async def store_a(unit_of_work) -> CreditSetup:
    setup = await add_credit_setup(unit_of_work)
    await add_purchase(unit_of_work, setup)
    await add_purchase(unit_of_work, setup, mode=PaymentMode.SINGLE_DATE)
    return setup


@pytest.fixture
async def store_b(unit_of_work, store_a) -> CreditSetup:
    """The same customer, with an account in a second store."""
    customer_id = (
        await CustomersFacade(unit_of_work).get_credit_terms(store_a.account_id)
    ).customer_id
    store = await add_store(unit_of_work, ruc="20999999991")
    account = await add_account(unit_of_work, store.id, customer_id, 14, 26)
    product = await add_product(unit_of_work, store.id)
    setup = CreditSetup(store.id, account.id, product.id, store_a.user_id)
    await add_purchase(unit_of_work, setup, mode=PaymentMode.SINGLE_DATE, quantity=2)
    return setup


@pytest.fixture
async def customer(unit_of_work, store_a, store_b) -> dict[str, str]:
    customer_id = (
        await CustomersFacade(unit_of_work).get_credit_terms(store_a.account_id)
    ).customer_id
    return authorization(
        sub=str(store_a.user_id), role="CUSTOMER", store_id=None, customer_id=customer_id
    )


@pytest.fixture
def admin_a(store_a) -> dict[str, str]:
    return authorization(sub=str(store_a.user_id), store_id=store_a.store_id)


async def test_customer_sees_both_stores(client, customer, store_a, store_b):
    response = await client.get("/api/v1/me/stores", headers=customer)

    assert response.json() == [
        {
            "store_id": store_a.store_id,
            "business_name": "Bodega de Prueba",
            "store_status": "ACTIVE",
            "account_status": "ACTIVE",
        },
        {
            "store_id": store_b.store_id,
            "business_name": "Bodega de Prueba",
            "store_status": "ACTIVE",
            "account_status": "ACTIVE",
        },
    ]


async def test_each_store_summary_has_only_its_own_debt(client, customer, store_a, store_b, on):
    on(date(2026, 11, 20))

    summary_a = (
        await client.get(f"/api/v1/me/stores/{store_a.store_id}/summary", headers=customer)
    ).json()
    summary_b = (
        await client.get(f"/api/v1/me/stores/{store_b.store_id}/summary", headers=customer)
    ).json()

    assert (summary_a["outstanding_principal"], summary_a["available_credit"]) == (
        "826.99",
        "673.01",
    )
    assert [(i["number"], i["amount"]) for i in summary_a["installments"]] == [
        (1, "109.68"),
        (2, "109.68"),
        (3, "109.68"),
        (4, "109.69"),
    ]
    assert (summary_b["outstanding_principal"], summary_b["installments"]) == ("200.00", [])
    assert (summary_a["credit_limit"], summary_a["tea"]) == ("1500.00", "75.0000000")


async def test_a_store_without_an_account_is_not_found(client, customer, unit_of_work):
    stranger = await add_store(unit_of_work, ruc="20999999992")

    response = await client.get(f"/api/v1/me/stores/{stranger.id}/summary", headers=customer)

    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


async def test_a_store_not_linked_to_the_portal_stays_hidden(
    client, customer, store_a, unit_of_work
):
    customer_id = (
        await CustomersFacade(unit_of_work).get_credit_terms(store_a.account_id)
    ).customer_id
    just_opened = await add_store(unit_of_work, ruc="20999999992")
    await add_account(unit_of_work, just_opened.id, customer_id, portal_linked=False)

    stores = await client.get("/api/v1/me/stores", headers=customer)
    summary = await client.get(f"/api/v1/me/stores/{just_opened.id}/summary", headers=customer)
    purchases = await client.get(f"/api/v1/me/stores/{just_opened.id}/purchases", headers=customer)

    assert len(stores.json()) == 2
    assert just_opened.id not in [store["store_id"] for store in stores.json()]
    assert (summary.status_code, summary.json()["code"]) == (404, "NOT_FOUND")
    assert purchases.status_code == 404


async def test_purchases_and_schedules_stay_in_their_store(client, customer, store_a, store_b):
    purchases_a = (
        await client.get(f"/api/v1/me/stores/{store_a.store_id}/purchases", headers=customer)
    ).json()
    purchases_b = (
        await client.get(f"/api/v1/me/stores/{store_b.store_id}/purchases", headers=customer)
    ).json()
    weekly = next(p for p in purchases_a if p["mode"] == "WEEKLY")

    schedule = await client.get(
        f"/api/v1/me/stores/{store_a.store_id}/purchases/{weekly['purchase_id']}/schedule",
        headers=customer,
    )
    crossed = await client.get(
        f"/api/v1/me/stores/{store_b.store_id}/purchases/{weekly['purchase_id']}/schedule",
        headers=customer,
    )

    assert sorted(p["amount"] for p in purchases_a) == ["400.00", "400.00"]
    assert [p["amount"] for p in purchases_b] == ["200.00"]
    assert [i["due_date"] for i in schedule.json()["installments"]] == [
        "2026-12-03",
        "2026-12-10",
        "2026-12-17",
        "2026-12-24",
    ]
    assert crossed.status_code == 404


async def test_statement_of_the_month(client, customer, store_a, on):
    on(date(2026, 11, 20))

    statement = await client.get(
        f"/api/v1/me/stores/{store_a.store_id}/cycles/2026/11", headers=customer
    )
    empty_month = await client.get(
        f"/api/v1/me/stores/{store_a.store_id}/cycles/2027/3", headers=customer
    )

    body = statement.json()
    assert (body["status"], body["capital"], body["ordinary_interest"], body["total"]) == (
        "CLOSED",
        "400.00",
        "26.99",
        "426.99",
    )
    assert empty_month.status_code == 404


async def test_dashboard_counts_overdue_installments_statements_and_the_cap(
    client, admin_a, store_a, on
):
    on(date(2026, 12, 5))

    dashboard = (await client.get("/api/v1/dashboard", headers=admin_a)).json()

    assert (dashboard["active_customers"], dashboard["outstanding_principal"]) == (1, "826.99")
    # Installment 1 (109.68, due 3/12) and the November statement (426.99, due 26/11).
    assert (
        dashboard["overdue_installments"],
        dashboard["overdue_statements"],
        dashboard["overdue_amount"],
    ) == (1, 1, "536.67")
    assert dashboard["purchases_this_month"]["count"] == 0
    assert dashboard["bcrp_cap"]["max_tea"] == "114.6800000"


async def test_dashboard_lists_what_falls_due_this_week_and_the_next_cutoff(
    client, admin_a, store_a, unit_of_work, on
):
    # Bought after the November cutoff, so it opens the December cycle (cutoff 14/12).
    await add_purchase(
        unit_of_work, store_a, datetime(2026, 11, 20, 9, tzinfo=LIMA), PaymentMode.SINGLE_DATE, 1
    )
    on(date(2026, 11, 26))
    payment_day = (await client.get("/api/v1/dashboard", headers=admin_a)).json()
    on(date(2026, 12, 3))
    first_installment_day = (await client.get("/api/v1/dashboard", headers=admin_a)).json()

    # On 26/11 the November statement falls due; installment 1 (3/12) is still 7 days away.
    assert payment_day["upcoming"] == [
        {
            "type": "CYCLE",
            "account_id": store_a.account_id,
            "customer_name": "Rosa Quispe Mamani",
            "due_date": "2026-11-26",
            "amount": "426.99",
        }
    ]
    # On 3/12 the November statement is overdue, so it is no longer upcoming.
    assert [
        (due["type"], due["due_date"], due["amount"]) for due in first_installment_day["upcoming"]
    ] == [("INSTALLMENT", "2026-12-03", "109.68")]
    assert payment_day["next_cutoff"] == first_installment_day["next_cutoff"] == "2026-12-14"


async def test_dashboard_month_counts_this_months_purchases(client, admin_a, store_a, on):
    on(date(2026, 10, 20))

    dashboard = (await client.get("/api/v1/dashboard", headers=admin_a)).json()

    # 26.99 of the single date purchase plus 11.74, the schedule interest of the weekly one.
    assert dashboard["purchases_this_month"] == {
        "count": 2,
        "amount": "800.00",
        "ordinary_interest": "38.73",
        "single_date_count": 1,
        "weekly_count": 1,
    }


async def test_report_adds_up_purchases_and_payments_of_the_period(client, admin_a, store_a, on):
    on(date(2026, 12, 3))
    installments = (
        await client.get("/api/v1/installments?status=PENDING", headers=admin_a)
    ).json()["items"]
    first = next(i for i in installments if i["number"] == 1)
    paid = await client.post(
        "/api/v1/payments",
        json={"kind": "INSTALLMENT", "installment_id": first["id"], "amount": "109.68"},
        headers=admin_a,
    )

    october = await client.get(
        "/api/v1/reports/summary?from=2026-10-01&to=2026-10-31", headers=admin_a
    )
    december = await client.get(
        "/api/v1/reports/summary?from=2026-12-01&to=2026-12-31", headers=admin_a
    )
    reversed_range = await client.get(
        "/api/v1/reports/summary?from=2026-12-31&to=2026-12-01", headers=admin_a
    )

    assert paid.status_code == 201
    assert (october.json()["purchases"]["count"], october.json()["payments"]["count"]) == (2, 0)
    assert december.json()["payments"] == {
        "count": 1,
        "total": "109.68",
        "principal": "105.01",
        "ordinary_interest": "4.67",
        "late_interest": "0.00",
        "savings": "0.00",
    }
    assert (reversed_range.json()["code"], reversed_range.json()["field"]) == (
        "INVALID_DATE_RANGE",
        "to",
    )


async def test_customers_and_store_admins_stay_on_their_side(client, customer, admin_a):
    assert (await client.get("/api/v1/dashboard", headers=customer)).status_code == 403
    assert (await client.get("/api/v1/me/stores", headers=admin_a)).status_code == 403
