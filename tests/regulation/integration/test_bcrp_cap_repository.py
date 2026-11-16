"""Tests for the BCRP cap repository against the migrated PostgreSQL database.

No test commits, so the seeded caps stay as they are.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap
from app.regulation.infrastructure.persistence.bcrp_cap_repository_impl import (
    BcrpCapRepositoryImpl,
)
from app.shared.domain.value_objects import Rate
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork


@pytest.fixture
async def repository():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield BcrpCapRepositoryImpl(unit_of_work.session)


async def test_finds_the_seeded_cap_in_force_on_each_side_of_its_change(repository):
    october = await repository.find_in_force(date(2026, 10, 31))
    november = await repository.find_in_force(date(2026, 11, 1))

    assert october.max_tea.percent == Decimal("114.1300000")
    assert november.max_tea.percent == Decimal("114.6800000")
    assert await repository.find_in_force(date(2027, 5, 1)) is None


async def test_lists_the_most_recent_cap_first(repository):
    caps = await repository.list_all()
    assert [cap.valid_from for cap in caps[:2]] == [date(2026, 11, 1), date(2026, 5, 1)]


async def test_detects_a_period_that_touches_an_existing_one(repository):
    assert await repository.exists_overlapping(date(2027, 4, 30), date(2027, 10, 31))
    assert not await repository.exists_overlapping(date(2027, 5, 1), date(2027, 10, 31))


async def test_adding_a_cap_sets_its_id(repository):
    cap = BcrpCap(Rate.from_percent(Decimal("110")), date(2027, 5, 1), date(2027, 10, 31))
    await repository.add(cap)
    assert cap.id is not None


async def test_database_rejects_overlapping_periods(repository):
    overlapping = BcrpCap(Rate.from_percent(Decimal("110")), date(2027, 4, 1), date(2027, 9, 30))
    with pytest.raises(IntegrityError):
        await repository.add(overlapping)
