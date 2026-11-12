"""Tests for the iam facade against the migrated PostgreSQL database. Nothing is committed."""

import pytest

from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.iam.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.iam.interfaces.acl.iam_facade import IamFacade, UserSummary
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Role
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork


@pytest.fixture
async def unit_of_work():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture
def facade(unit_of_work):
    return IamFacade(unit_of_work)


async def stored_password_hash(unit_of_work, user_id: int) -> str:
    user = await UserRepositoryImpl(unit_of_work.session).find_by_id(user_id)
    assert user is not None
    return user.password_hash


async def test_store_admin_is_created_with_a_hashed_password(facade, unit_of_work):
    user_id = await facade.create_store_admin(
        "Rosa@Bodega-Test.pe", "Rosa Quispe", "clave-de-rosa", store_id=3
    )

    summary = await facade.find_user_by_username("rosa@bodega-test.pe")
    password_hash = await stored_password_hash(unit_of_work, user_id)
    assert summary == UserSummary(user_id, "rosa@bodega-test.pe", Role.STORE_ADMIN, True)
    assert password_hash != "clave-de-rosa"
    assert (await Argon2PasswordHasher().verify("clave-de-rosa", password_hash))[0]


async def test_repeated_email_is_rejected(facade):
    await facade.create_store_admin("rosa@bodega-test.pe", "Rosa", "clave-de-rosa", store_id=3)

    with pytest.raises(BusinessError) as error:
        await facade.create_store_admin("ROSA@bodega-test.pe", "Otra", "otra-clave", store_id=4)

    assert (error.value.code, error.value.status, error.value.field) == (
        "EMAIL_TAKEN",
        409,
        "email",
    )


async def test_customer_user_is_named_after_the_dni(facade, unit_of_work):
    credentials = await facade.create_customer_user("70000001")

    summary = await facade.find_user_by_username("70000001")
    assert credentials.username == "70000001"
    assert summary == UserSummary(credentials.user_id, "70000001", Role.CUSTOMER, True)
    assert (
        await Argon2PasswordHasher().verify(
            credentials.temporary_password,
            await stored_password_hash(unit_of_work, credentials.user_id),
        )
    )[0]


async def test_dni_with_a_user_is_rejected(facade):
    await facade.create_customer_user("70000001")

    with pytest.raises(BusinessError) as error:
        await facade.create_customer_user("70000001")

    assert (error.value.code, error.value.status) == ("USERNAME_TAKEN", 409)


async def test_reset_gives_a_new_temporary_password(facade, unit_of_work):
    first = await facade.create_customer_user("70000001")

    reset = await facade.reset_password(first.user_id)

    assert (reset.user_id, reset.username) == (first.user_id, "70000001")
    assert reset.temporary_password != first.temporary_password
    password_hash = await stored_password_hash(unit_of_work, first.user_id)
    assert (await Argon2PasswordHasher().verify(reset.temporary_password, password_hash))[0]


async def test_reset_of_a_missing_user_is_not_found(facade):
    with pytest.raises(BusinessError) as error:
        await facade.reset_password(999_999)
    assert (error.value.code, error.value.status) == ("NOT_FOUND", 404)


async def test_unknown_username_is_none(facade):
    assert await facade.find_user_by_username("nadie@bodega-test.pe") is None
