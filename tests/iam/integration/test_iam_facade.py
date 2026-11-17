"""Tests for the iam facade against the migrated PostgreSQL database. Nothing is committed."""

import pytest

from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.iam.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.iam.interfaces.acl.iam_facade import IamFacade, UserSummary
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Role
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork
from tests.stored_store import add_store


@pytest.fixture
async def unit_of_work():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture
async def store_id(unit_of_work) -> int:
    return (await add_store(unit_of_work)).id


@pytest.fixture
def facade(unit_of_work):
    return IamFacade(unit_of_work)


async def stored_password_hash(unit_of_work, user_id: int) -> str:
    user = await UserRepositoryImpl(unit_of_work.session).find_by_id(user_id)
    assert user is not None
    return user.password_hash


async def test_store_admin_is_created_with_a_hashed_password(facade, unit_of_work, store_id):
    user_id = await facade.create_store_admin(
        "Rosa@Bodega-Test.pe", "Rosa Quispe", "clave-de-rosa", store_id
    )

    summary = await facade.find_user_by_username("rosa@bodega-test.pe")
    password_hash = await stored_password_hash(unit_of_work, user_id)
    assert summary == UserSummary(user_id, "rosa@bodega-test.pe", Role.STORE_ADMIN, True)
    assert password_hash != "clave-de-rosa"
    assert (await Argon2PasswordHasher().verify("clave-de-rosa", password_hash))[0]


async def test_repeated_email_is_rejected(facade, store_id):
    await facade.create_store_admin("rosa@bodega-test.pe", "Rosa", "clave-de-rosa", store_id)

    with pytest.raises(BusinessError) as error:
        await facade.create_store_admin("ROSA@bodega-test.pe", "Otra", "otra-clave", store_id)

    assert (error.value.code, error.value.status, error.value.field) == (
        "EMAIL_TAKEN",
        409,
        "email",
    )


async def test_customer_user_is_named_after_the_dni_with_a_password_nobody_knows(
    facade, unit_of_work
):
    user_id = await facade.create_customer_user("70000001")

    summary = await facade.find_user_by_username("70000001")
    password_hash = await stored_password_hash(unit_of_work, user_id)
    assert summary == UserSummary(user_id, "70000001", Role.CUSTOMER, True)
    for guess in ("70000001", ""):
        assert not (await Argon2PasswordHasher().verify(guess, password_hash))[0]


async def test_dni_with_a_user_is_rejected(facade):
    await facade.create_customer_user("70000001")

    with pytest.raises(BusinessError) as error:
        await facade.create_customer_user("70000001")

    assert (error.value.code, error.value.status) == ("USERNAME_TAKEN", 409)


async def test_unknown_username_is_none(facade):
    assert await facade.find_user_by_username("nadie@bodega-test.pe") is None


async def test_a_token_is_current_until_the_password_changes(facade, unit_of_work):
    users = UserRepositoryImpl(unit_of_work.session)
    user = await users.find_by_id(await facade.create_customer_user("70000001"))
    assert user is not None and user.id is not None
    issued_with = user.password_version

    assert await facade.is_password_current(user.id, issued_with)
    user.change_password("another hash")
    await users.update(user)

    assert not await facade.is_password_current(user.id, issued_with)
    assert await facade.is_password_current(user.id, issued_with + 1)
    assert not await facade.is_password_current(999_999, 0)
