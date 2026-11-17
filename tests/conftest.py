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
