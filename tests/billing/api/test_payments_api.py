"""Tests for the payment and cycle endpoints against the migrated PostgreSQL database.

They follow the report's test N°3: S/ 400 bought on 15/10/2026 by an account with TEA 75%,
late TEA 90%, cutoff 14 and payment 26. Its cycle is November (cutoff 14/11, payment 26/11).
Weekly without grace, it is 4 installments of 102.75 due every 7 days from the purchase:
22/10, 29/10, 05/11 and 12/11. Single date, it owes 400 + 26.99 on 26/11.

Every test shares one Unit of Work that never commits, and sets the day it runs on.
"""

from datetime import date, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.billing.interfaces.acl.billing_facade import BillingFacade
from app.credit.domain.model.aggregates.purchase import PaymentMode
from app.credit.interfaces.acl.credit_facade import CreditFacade
from app.main import app as application
from app.shared.infrastructure.unit_of_work import get_unit_of_work
from app.shared.interfaces.rest.business_date import get_business_now, get_business_today
from tests.authorization import authorization
from tests.credit.stored_credit import LIMA, add_credit_setup, add_purchase


@pytest.fixture
async def client(unit_of_work):
    application.dependency_overrides[get_unit_of_work] = lambda: unit_of_work
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    application.dependency_overrides.clear()


def on(day: date) -> None:
    """Make the API run on that day in Lima."""
    application.dependency_overrides[get_business_today] = lambda: day
    application.dependency_overrides[get_business_now] = lambda: datetime(
        day.year, day.month, day.day, 12, tzinfo=LIMA
    )


@pytest.fixture
async def setup(unit_of_work):
    return await add_credit_setup(unit_of_work)


@pytest.fixture
def admin(setup) -> dict[str, str]:
    return authorization(sub=str(setup.user_id), store_id=setup.store_id)


@pytest.fixture
async def weekly(unit_of_work, setup):
    return await add_purchase(unit_of_work, setup)


@pytest.fixture
async def single_date(unit_of_work, setup):
    return await add_purchase(unit_of_work, setup, mode=PaymentMode.SINGLE_DATE)


async def quote(client, headers, **target):
    return await client.post("/api/v1/payments/quote", json=target, headers=headers)


async def pay(client, headers, amount: str, **target):
    return await client.post("/api/v1/payments", json=target | {"amount": amount}, headers=headers)


def amounts(body) -> tuple[str, str, str, str, str]:
    return (
        body["late_interest"],
        body["ordinary_interest"],
        body["principal"],
        body["total"],
        body["savings"],
    )


async def test_installment_paid_on_its_due_date_has_no_late_interest(
    client, admin, weekly, unit_of_work
):
    on(date(2026, 10, 22))
    first = weekly.installments[0].id

    quoted = await quote(client, admin, kind="INSTALLMENT", installment_id=first)
    paid = await pay(client, admin, "102.75", kind="INSTALLMENT", installment_id=first)

    assert amounts(quoted.json()) == ("0.00", "4.38", "98.37", "102.75", "0.00")
    assert paid.status_code == 201
    assert (paid.json()["kind"], paid.json()["paid_on"]) == ("INSTALLMENT", "2026-10-22")
    installment = await CreditFacade(unit_of_work).get_installment(first)
    assert installment.status == "PAID"


async def test_late_installment_pays_late_interest_first_and_no_partial_payment(
    client, admin, weekly
):
    on(date(2026, 10, 25))
    first = weekly.installments[0].id

    quoted = await quote(client, admin, kind="INSTALLMENT", installment_id=first)
    partial = await pay(client, admin, "102.75", kind="INSTALLMENT", installment_id=first)
    paid = await pay(client, admin, "103.30", kind="INSTALLMENT", installment_id=first)

    # 102.75 x ((1 + 90%)^(3/360) - 1) = 0.55: the annual late rate, charged by the day.
    assert amounts(quoted.json()) == ("0.55", "4.38", "98.37", "103.30", "0.00")
    assert quoted.json()["days_late"] == 3
    assert (partial.status_code, partial.json()["code"]) == (422, "PARTIAL_PAYMENT_NOT_ALLOWED")
    assert amounts(paid.json()) == ("0.55", "4.38", "98.37", "103.30", "0.00")


async def test_installment_advance_pays_the_full_installment_in_order(client, admin, weekly):
    on(date(2026, 10, 20))
    first, second = weekly.installments[0].id, weekly.installments[1].id

    out_of_order = await quote(client, admin, kind="INSTALLMENT_ADVANCE", installment_id=second)
    not_due = await quote(client, admin, kind="INSTALLMENT", installment_id=first)
    paid = await pay(client, admin, "102.75", kind="INSTALLMENT_ADVANCE", installment_id=first)
    again = await pay(client, admin, "102.75", kind="INSTALLMENT_ADVANCE", installment_id=first)

    assert (out_of_order.status_code, out_of_order.json()["code"]) == (
        409,
        "INSTALLMENT_OUT_OF_ORDER",
    )
    assert (not_due.json()["code"], not_due.json()["field"]) == ("PAYMENT_KIND_MISMATCH", "kind")
    assert amounts(paid.json()) == ("0.00", "4.38", "98.37", "102.75", "0.00")
    assert (again.status_code, again.json()["code"]) == (409, "ALREADY_PAID")


async def test_single_date_paid_early_charges_only_the_days_used(
    client, admin, single_date, unit_of_work
):
    on(date(2026, 11, 5))

    paid = await pay(client, admin, "413.27", kind="SINGLE_DATE_EARLY", purchase_id=single_date.id)

    # 21 of the 42 days: 13.27 of interest instead of 26.99.
    assert paid.status_code == 201
    assert amounts(paid.json()) == ("0.00", "13.27", "400.00", "413.27", "13.72")
    assert (await CreditFacade(unit_of_work).get_purchase(single_date.id)).status == "PAID"


async def test_single_date_billed_in_a_closed_cycle_is_paid_with_the_statement(
    client, admin, single_date
):
    on(date(2026, 11, 20))

    early = await quote(client, admin, kind="SINGLE_DATE_EARLY", purchase_id=single_date.id)

    assert (early.status_code, early.json()["code"]) == (409, "PURCHASE_IN_STATEMENT")


async def test_cycle_statement_is_paid_once_closed_with_late_interest_after_its_date(
    client, admin, setup, single_date
):
    cycle_id = single_date.cycle_id
    on(date(2026, 11, 10))
    still_open = await quote(client, admin, kind="CYCLE_STATEMENT", cycle_id=cycle_id)
    on(date(2026, 11, 20))
    on_time = await quote(client, admin, kind="CYCLE_STATEMENT", cycle_id=cycle_id)
    on(date(2026, 11, 29))
    late = await quote(client, admin, kind="CYCLE_STATEMENT", cycle_id=cycle_id)
    paid = await pay(client, admin, "429.28", kind="CYCLE_STATEMENT", cycle_id=cycle_id)
    statement = await client.get(
        f"/api/v1/customers/{setup.account_id}/cycles/2026/11", headers=admin
    )

    assert (still_open.status_code, still_open.json()["code"]) == (409, "CYCLE_NOT_CLOSED")
    assert amounts(on_time.json()) == ("0.00", "26.99", "400.00", "426.99", "0.00")
    # 426.99 x ((1 + 90%)^(3/360) - 1) = 2.29 of late interest.
    assert amounts(late.json()) == ("2.29", "26.99", "400.00", "429.28", "0.00")
    assert paid.status_code == 201
    body = statement.json()
    assert (body["status"], body["late_interest"], body["total"]) == ("PAID", "2.29", "429.28")
    assert [p["status"] for p in body["purchases"]] == ["PAID"]


async def test_overdue_statement_shows_the_late_interest_to_date(client, admin, setup, single_date):
    on(date(2026, 11, 29))

    statement = await client.get(
        f"/api/v1/customers/{setup.account_id}/cycles/2026/11", headers=admin
    )
    overdue = await client.get("/api/v1/cycles?status=OVERDUE", headers=admin)

    assert (statement.json()["status"], statement.json()["late_interest"]) == ("OVERDUE", "2.29")
    assert [cycle["id"] for cycle in overdue.json()["items"]] == [single_date.cycle_id]


async def test_statement_downloads_as_a_pdf(client, admin, setup, single_date):
    on(date(2026, 11, 20))

    pdf = await client.get(
        f"/api/v1/customers/{setup.account_id}/cycles/2026/11/pdf", headers=admin
    )
    empty_month = await client.get(
        f"/api/v1/customers/{setup.account_id}/cycles/2027/3/pdf", headers=admin
    )

    assert (pdf.status_code, pdf.headers["content-type"]) == (200, "application/pdf")
    assert pdf.headers["content-disposition"] == 'attachment; filename="estado-2026-11.pdf"'
    assert pdf.content.startswith(b"%PDF")
    assert empty_month.status_code == 404


async def test_full_prepayment_charges_interest_since_the_last_due_date(
    client, admin, weekly, unit_of_work
):
    on(date(2026, 10, 22))
    await pay(client, admin, "102.75", kind="INSTALLMENT", installment_id=weekly.installments[0].id)
    # 4 days after the first installment: the 301.63 left plus its interest since then.
    on(date(2026, 10, 26))

    paid = await pay(client, admin, "303.51", kind="FULL_PREPAYMENT", purchase_id=weekly.id)

    assert paid.status_code == 201
    assert amounts(paid.json()) == ("0.00", "1.88", "301.63", "303.51", "4.74")
    assert (await CreditFacade(unit_of_work).get_purchase(weekly.id)).status == "PREPAID"


async def test_full_prepayment_in_the_grace_weeks_charges_the_days_since_the_purchase(
    client, admin, setup, unit_of_work
):
    # 1 week of grace, then 3 installments of 137.75 from 29/10.
    graced = await add_purchase(unit_of_work, setup, installments_count=3, grace_weeks=1)
    on(date(2026, 10, 20))

    quoted = await quote(client, admin, kind="FULL_PREPAYMENT", purchase_id=graced.id)

    assert amounts(quoted.json()) == ("0.00", "3.12", "400.00", "403.12", "10.13")
    assert quoted.json()["interest_days"] == 5


async def test_full_prepayment_is_rejected_with_an_overdue_installment(client, admin, weekly):
    on(date(2026, 10, 24))

    quoted = await quote(client, admin, kind="FULL_PREPAYMENT", purchase_id=weekly.id)

    assert (quoted.status_code, quoted.json()["code"]) == (409, "PREPAYMENT_WITH_OVERDUE")


@pytest.mark.parametrize(
    ("target", "field"),
    [
        ({"kind": "INSTALLMENT"}, "installment_id"),
        ({"kind": "CYCLE_STATEMENT", "cycle_id": 1, "purchase_id": 2}, "purchase_id"),
    ],
)
async def test_the_kind_needs_its_own_target(client, admin, target, field):
    response = await quote(client, admin, **target)

    assert (response.json()["code"], response.json()["field"]) == ("INVALID_PAYMENT_TARGET", field)


async def test_a_prepayment_is_for_weekly_purchases(client, admin, single_date):
    on(date(2026, 11, 5))

    response = await quote(client, admin, kind="FULL_PREPAYMENT", purchase_id=single_date.id)

    assert (response.json()["code"], response.json()["field"]) == (
        "INVALID_PAYMENT_TARGET",
        "purchase_id",
    )


async def test_targets_of_another_store_are_not_found(client, weekly, unit_of_work):
    other = await add_credit_setup(unit_of_work, ruc="20999999991", dni="70000002")
    other_admin = authorization(sub=str(other.user_id), store_id=other.store_id)
    on(date(2026, 10, 22))

    response = await quote(
        client, other_admin, kind="INSTALLMENT", installment_id=weekly.installments[0].id
    )
    statement = await client.get(
        f"/api/v1/customers/{weekly.account_id}/cycles/2026/11", headers=other_admin
    )
    pdf = await client.get(
        f"/api/v1/customers/{weekly.account_id}/cycles/2026/11/pdf", headers=other_admin
    )

    assert (response.status_code, statement.status_code, pdf.status_code) == (404, 404, 404)


async def test_payments_are_listed_most_recent_first(client, admin, setup, weekly, unit_of_work):
    on(date(2026, 10, 22))
    await pay(client, admin, "102.75", kind="INSTALLMENT", installment_id=weekly.installments[0].id)
    on(date(2026, 10, 29))
    await pay(client, admin, "102.75", kind="INSTALLMENT", installment_id=weekly.installments[1].id)

    listed = await client.get("/api/v1/payments", headers=admin)
    filtered = await client.get("/api/v1/payments?from=2026-10-25", headers=admin)

    assert [p["paid_on"] for p in listed.json()["items"]] == ["2026-10-29", "2026-10-22"]
    assert filtered.json()["total"] == 1
    summaries = await BillingFacade(unit_of_work).list_payments(setup.account_id)
    assert [s.paid_on for s in summaries] == [date(2026, 10, 29), date(2026, 10, 22)]
