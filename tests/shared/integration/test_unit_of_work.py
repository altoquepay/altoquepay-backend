"""Tests for the Unit of Work against the real PostgreSQL database."""

import pytest
from sqlalchemy import text

from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork

PROBE_TABLE = "unit_of_work_probe"


async def probe_table_exists() -> bool:
    async with UnitOfWork(session_factory) as unit_of_work:
        result = await unit_of_work.session.execute(
            text("SELECT to_regclass(:table_name)"), {"table_name": PROBE_TABLE}
        )
        return result.scalar() is not None


async def create_probe_table(unit_of_work: UnitOfWork) -> None:
    await unit_of_work.session.execute(text(f"CREATE TABLE {PROBE_TABLE} (id integer)"))


@pytest.fixture(autouse=True)
async def drop_probe_table():
    yield
    async with UnitOfWork(session_factory) as unit_of_work:
        await unit_of_work.session.execute(text(f"DROP TABLE IF EXISTS {PROBE_TABLE}"))
        await unit_of_work.commit()


async def test_committed_work_persists():
    async with UnitOfWork(session_factory) as unit_of_work:
        await create_probe_table(unit_of_work)
        await unit_of_work.commit()

    assert await probe_table_exists()


async def test_uncommitted_work_is_discarded():
    async with UnitOfWork(session_factory) as unit_of_work:
        await create_probe_table(unit_of_work)

    assert not await probe_table_exists()


async def test_exception_discards_work_and_propagates():
    with pytest.raises(RuntimeError):
        async with UnitOfWork(session_factory) as unit_of_work:
            await create_probe_table(unit_of_work)
            raise RuntimeError

    assert not await probe_table_exists()
