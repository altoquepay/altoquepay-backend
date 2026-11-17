"""Run every test on its own database, so tests never touch the one used for manual checks.

Pytest loads this file before the test modules, so the application only ever sees the test URL.
"""

import asyncio
import os
import subprocess
import sys

import asyncpg
import pytest
from sqlalchemy import make_url

from app.iam.interfaces.rest.sign_in_attempts import sign_in_attempts
from app.shared.infrastructure.config import Settings

development_database_url = make_url(Settings().database_url)
test_database_url = development_database_url.set(
    database=f"{development_database_url.database}_test"
)
# Environment variables take precedence over .env for the application and Alembic.
os.environ["DATABASE_URL"] = test_database_url.render_as_string(hide_password=False)

# Imported only now: the engine reads DATABASE_URL when its module loads.
from app.iam.domain.model.aggregates.user import User  # noqa: E402
from app.iam.domain.model.value_objects.email import Email  # noqa: E402
from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl  # noqa: E402
from app.shared.domain.value_objects import Dni, Role  # noqa: E402
from app.shared.infrastructure.database import session_factory  # noqa: E402
from app.shared.infrastructure.unit_of_work import UnitOfWork  # noqa: E402
from tests.authorization import authorization  # noqa: E402
from tests.stored_store import add_store  # noqa: E402


async def create_test_database_if_missing() -> None:
    server_url = test_database_url.set(drivername="postgresql", database="postgres")
    connection = await asyncpg.connect(server_url.render_as_string(hide_password=False))
    try:
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", test_database_url.database
        )
        if not exists:
            await connection.execute(f'CREATE DATABASE "{test_database_url.database}"')
    finally:
        await connection.close()


def pytest_sessionstart(session) -> None:
    asyncio.run(create_test_database_if_missing())
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest.fixture(autouse=True)
def forget_sign_in_attempts() -> None:
    """Every test signs in from the same IP, so each one starts with no attempts counted."""
    sign_in_attempts.clear()


class RollbackUnitOfWork(UnitOfWork):
    """Commits only flush, so everything a test writes is rolled back when it ends."""

    async def commit(self) -> None:
        await self.session.flush()


@pytest.fixture
async def unit_of_work():
    async with RollbackUnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture
async def stored_system_admin(unit_of_work) -> dict[str, str]:
    """Headers of a system admin that exists, so the token passes the password check."""
    admin = User("system-admin@test.pe", "unused-hash", Role.SYSTEM_ADMIN)
    await UserRepositoryImpl(unit_of_work.session).add(admin)
    return authorization(sub=str(admin.id), role="SYSTEM_ADMIN", store_id=None)


@pytest.fixture
async def stored_store_admin(unit_of_work) -> dict[str, str]:
    """Headers of the administrator of a new store, both stored."""
    store = await add_store(unit_of_work, ruc="20999999981")
    admin = User.store_admin(Email("admin@tienda-test.pe"), "Admin", "unused-hash", store.id)
    await UserRepositoryImpl(unit_of_work.session).add(admin)
    return authorization(sub=str(admin.id), store_id=store.id)


@pytest.fixture
async def stored_customer_user(unit_of_work) -> dict[str, str]:
    """Headers of a customer's stored user, for routes a customer must not reach."""
    user = User.customer(Dni("40000009"), "unused-hash")
    await UserRepositoryImpl(unit_of_work.session).add(user)
    return authorization(sub=str(user.id), role="CUSTOMER", store_id=None)
