"""Tests for BillingFacade.get_or_open_cycle against the migrated PostgreSQL database.

Nothing is committed. The cases come from the guide for credit and the report's tests.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.billing.domain.model.aggregates.billing_cycle import BillingCycle, CycleStatus
from app.billing.domain.services.cycle_assignment import cycle_period_of
from app.billing.infrastructure.persistence.billing_cycle_repository_impl import (
    BillingCycleRepositoryImpl,
)
from app.billing.interfaces.acl.billing_facade import BillingFacade, CycleReference
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork
from tests.stored_account import add_account, add_customer
from tests.stored_store import add_store

LIMA = ZoneInfo("America/Lima")


@pytest.fixture
async def unit_of_work():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


async def new_account(unit_of_work, cutoff_day: int, payment_day: int) -> int:
    store = await add_store(unit_of_work)
    customer = await add_customer(unit_of_work)
    account = await add_account(unit_of_work, store.id, customer.id, cutoff_day, payment_day)
    assert account.id is not None
    return account.id


@pytest.mark.parametrize(
    ("purchased_at", "cutoff_day", "payment_day", "year", "month", "payment_date"),
    [
        (datetime(2026, 9, 15, 10, tzinfo=LIMA), 20, 26, 2026, 9, date(2026, 9, 26)),
        (datetime(2026, 9, 20, 23, 59, 59, tzinfo=LIMA), 20, 26, 2026, 9, date(2026, 9, 26)),
        (datetime(2026, 9, 21, 0, 0, 0, tzinfo=LIMA), 20, 26, 2026, 10, date(2026, 10, 26)),
        (datetime(2026, 9, 21, 3, 0, 0, tzinfo=UTC), 20, 26, 2026, 9, date(2026, 9, 26)),
        (datetime(2026, 10, 15, 12, tzinfo=LIMA), 14, 26, 2026, 11, date(2026, 11, 26)),
        (datetime(2026, 12, 20, 12, tzinfo=LIMA), 14, 26, 2027, 1, date(2027, 1, 26)),
    ],
    ids=[
        "report test 1",
        "last second of the cutoff",
        "first second after the cutoff",
        "UTC already the 21st, Lima still the 20th",
        "report test 3",
        "new year",
    ],
)
async def test_purchase_gets_the_cycle_of_its_day_in_lima(
    unit_of_work, purchased_at, cutoff_day, payment_day, year, month, payment_date
):
    account_id = await new_account(unit_of_work, cutoff_day, payment_day)

    cycle = await BillingFacade(unit_of_work).get_or_open_cycle(account_id, purchased_at)

    assert cycle == CycleReference(
        cycle.cycle_id, year, month, date(year, month, cutoff_day), payment_date
    )


async def test_same_cycle_is_returned_twice(unit_of_work):
    account_id = await new_account(unit_of_work, 20, 26)
    facade = BillingFacade(unit_of_work)

    first = await facade.get_or_open_cycle(account_id, datetime(2026, 9, 1, tzinfo=LIMA))
    second = await facade.get_or_open_cycle(account_id, datetime(2026, 9, 20, tzinfo=LIMA))

    assert first == second


async def test_purchase_in_a_closed_cycle_is_rejected(unit_of_work):
    account_id = await new_account(unit_of_work, 20, 26)
    period = cycle_period_of(date(2026, 9, 15), 20, 26)
    closed = BillingCycle.open(account_id, period)
    closed.status = CycleStatus.CLOSED
    await BillingCycleRepositoryImpl(unit_of_work.session).add(closed)

    with pytest.raises(BusinessError) as error:
        await BillingFacade(unit_of_work).get_or_open_cycle(
            account_id, datetime(2026, 9, 15, 10, tzinfo=LIMA)
        )

    assert (error.value.code, error.value.status) == ("CYCLE_CLOSED", 409)


async def test_unknown_account_is_not_found(unit_of_work):
    with pytest.raises(BusinessError) as error:
        await BillingFacade(unit_of_work).get_or_open_cycle(
            999_999, datetime(2026, 9, 15, tzinfo=LIMA)
        )

    assert (error.value.code, error.value.status) == ("NOT_FOUND", 404)


async def test_purchase_time_without_time_zone_is_refused(unit_of_work):
    account_id = await new_account(unit_of_work, 20, 26)

    with pytest.raises(ValueError):
        await BillingFacade(unit_of_work).get_or_open_cycle(account_id, datetime(2026, 9, 15))
