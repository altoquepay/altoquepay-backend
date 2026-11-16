"""Unit of Work: one database transaction per request, shared by all bounded contexts."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.infrastructure.database import session_factory


class UnitOfWork:
    """Groups the writes of a use case so they are confirmed together or not at all."""

    def __init__(self, new_session: async_sessionmaker[AsyncSession]) -> None:
        self._new_session = new_session

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._new_session()
        return self

    async def __aexit__(self, exception_type, exception, traceback) -> None:
        # Closing rolls back anything not committed, so a failed use case leaves no partial writes.
        await self.session.close()

    async def commit(self) -> None:
        """Confirm the transaction. Call it from the use case, once all its work succeeded."""
        await self.session.commit()


async def get_unit_of_work() -> AsyncIterator[UnitOfWork]:
    """FastAPI dependency that provides the Unit of Work of the current request."""
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work
