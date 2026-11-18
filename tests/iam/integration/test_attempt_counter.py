"""Tests for the attempt counter, which commits for real; conftest empties its table per test."""

import asyncio
from datetime import timedelta

from sqlalchemy import func, select, update

from app.iam.infrastructure.persistence.attempt_counter import count_attempt
from app.iam.infrastructure.persistence.models import SignInAttemptModel
from app.shared.infrastructure.database import session_factory

KEY = "ip:203.0.113.5"
OTHER_KEY = "ip:198.51.100.7"


async def start_window_minutes_ago(key: str, minutes: int) -> None:
    async with session_factory() as session:
        await session.execute(
            update(SignInAttemptModel)
            .where(SignInAttemptModel.key == key)
            .values(window_started_at=func.now() - timedelta(minutes=minutes))
        )
        await session.commit()


async def test_parallel_attempts_on_separate_connections_are_each_counted_once():
    counts = await asyncio.gather(*(count_attempt(KEY) for _ in range(25)))

    assert sorted(counts) == list(range(1, 26))


async def test_a_window_older_than_15_minutes_starts_again():
    await count_attempt(KEY)
    await count_attempt(KEY)
    await start_window_minutes_ago(KEY, 16)

    assert await count_attempt(KEY) == 1


async def test_expired_windows_are_deleted():
    await count_attempt(OTHER_KEY)
    await start_window_minutes_ago(OTHER_KEY, 16)

    await count_attempt(KEY)

    async with session_factory() as session:
        assert list(await session.scalars(select(SignInAttemptModel.key))) == [KEY]
