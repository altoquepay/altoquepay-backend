"""Counts sign-in and reset attempts in the database, so every API process shares the count."""

from datetime import timedelta

from sqlalchemy import case, delete, func
from sqlalchemy.dialects.postgresql import insert

from app.iam.infrastructure.persistence.models import SignInAttemptModel
from app.shared.infrastructure.database import session_factory

WINDOW = timedelta(minutes=15)


async def count_attempt(key: str) -> int:
    """Count one more attempt for the key and return how many it has in its 15-minute window.

    It commits on a session of its own, so the attempt counts even when the request fails and
    rolls back, and it reads the database clock, so every process agrees on when a window ends.
    """
    window_expired = SignInAttemptModel.window_started_at <= func.now() - WINDOW
    statement = (
        insert(SignInAttemptModel)
        .values(key=key, window_started_at=func.now(), attempts=1)
        .on_conflict_do_update(
            index_elements=[SignInAttemptModel.key],
            set_={
                "window_started_at": case(
                    (window_expired, func.now()), else_=SignInAttemptModel.window_started_at
                ),
                "attempts": case((window_expired, 1), else_=SignInAttemptModel.attempts + 1),
            },
        )
        .returning(SignInAttemptModel.attempts)
    )
    async with session_factory() as session:
        attempts = await session.scalar(statement)
        await session.commit()
        # Apart from the count, so counting locks one row and never waits on this cleanup.
        await session.execute(delete(SignInAttemptModel).where(window_expired))
        await session.commit()
    return attempts
