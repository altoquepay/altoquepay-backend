"""Tests for signing in and changing passwords, with in-memory ports."""

import pytest

from app.iam.application.command_services.authentication_service import AuthenticationService
from app.iam.application.ports.token_service import TokenClaims
from app.iam.domain.model.aggregates.user import User
from app.iam.domain.model.commands.change_password_command import ChangePasswordCommand
from app.iam.domain.model.commands.sign_in_command import SignInCommand
from app.iam.domain.model.value_objects.email import Email
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni, Role
from tests.iam.fakes import (
    ClaimsAsToken,
    CountingUnitOfWork,
    FixedCustomers,
    FixedStores,
    InMemoryUsers,
    PlainHasher,
)


class Context:
    def __init__(self) -> None:
        self.users = InMemoryUsers()
        self.hasher = PlainHasher()
        self.tokens = ClaimsAsToken()
        self.stores = FixedStores()
        self.unit_of_work = CountingUnitOfWork()
        self.service = AuthenticationService(
            self.users,
            self.hasher,
            self.tokens,
            self.stores,
            FixedCustomers(),
            self.unit_of_work,  # type: ignore[arg-type]
        )

    async def add(self, user: User) -> User:
        await self.users.add(user)
        return user


@pytest.fixture
def context():
    return Context()


async def test_store_admin_signs_in_with_the_email_in_any_case(context):
    admin = await context.add(
        User.store_admin(Email("rosa@bodega.pe"), "Rosa", "hashed:clave-rosa", store_id=3)
    )

    signed_in = await context.service.sign_in(SignInCommand(" Rosa@Bodega.PE", "clave-rosa"))

    assert signed_in.access_token == "token-1"
    assert context.tokens.issued == [
        TokenClaims(admin.id, Role.STORE_ADMIN, must_change_password=False, store_id=3)
    ]


async def test_customer_token_carries_the_person_and_the_password_block(context):
    customer = await context.add(User.customer(Dni("01234567"), "hashed:Temporal7k"))

    await context.service.sign_in(SignInCommand("01234567", "Temporal7k"))

    assert context.tokens.issued == [
        TokenClaims(customer.id, Role.CUSTOMER, must_change_password=True, customer_id=100)
    ]


async def test_system_admin_token_has_no_store_nor_customer(context):
    await context.add(User("admin@altoquepay.pe", "hashed:clave-admin", Role.SYSTEM_ADMIN))

    await context.service.sign_in(SignInCommand("admin@altoquepay.pe", "clave-admin"))

    claims = context.tokens.issued[0]
    assert (claims.role, claims.store_id, claims.customer_id) == (Role.SYSTEM_ADMIN, None, None)


@pytest.mark.parametrize(
    ("username", "password"),
    [("rosa@bodega.pe", "wrong-password"), ("nadie@bodega.pe", "clave-rosa")],
)
async def test_unknown_user_and_wrong_password_get_the_same_answer(context, username, password):
    await context.add(
        User.store_admin(Email("rosa@bodega.pe"), "Rosa", "hashed:clave-rosa", store_id=3)
    )

    with pytest.raises(BusinessError) as error:
        await context.service.sign_in(SignInCommand(username, password))

    assert (error.value.code, error.value.status) == ("INVALID_CREDENTIALS", 401)
    assert context.tokens.issued == []


async def test_unknown_user_still_costs_a_password_check(context):
    with pytest.raises(BusinessError):
        await context.service.sign_in(SignInCommand("nadie@bodega.pe", "clave"))

    assert context.hasher.checks_without_user == 1


async def test_deactivated_user_cannot_sign_in(context):
    user = User("admin@altoquepay.pe", "hashed:clave-admin", Role.SYSTEM_ADMIN, is_active=False)
    await context.add(user)

    with pytest.raises(BusinessError) as error:
        await context.service.sign_in(SignInCommand("admin@altoquepay.pe", "clave-admin"))

    assert (error.value.code, error.value.status) == ("USER_INACTIVE", 403)


async def test_admin_of_an_inactive_store_cannot_sign_in(context):
    await context.add(
        User.store_admin(Email("rosa@bodega.pe"), "Rosa", "hashed:clave-rosa", store_id=3)
    )
    context.stores.inactive_store_ids.add(3)

    with pytest.raises(BusinessError) as error:
        await context.service.sign_in(SignInCommand("rosa@bodega.pe", "clave-rosa"))

    assert (error.value.code, error.value.status) == ("STORE_INACTIVE", 403)


async def test_outdated_hash_is_replaced_on_sign_in(context):
    admin = await context.add(User("admin@altoquepay.pe", "old:clave-admin", Role.SYSTEM_ADMIN))

    await context.service.sign_in(SignInCommand("admin@altoquepay.pe", "clave-admin"))

    assert context.users.stored[admin.id].password_hash == "hashed:clave-admin"
    assert context.unit_of_work.commits == 1


async def test_sign_in_writes_nothing_when_the_hash_is_current(context):
    await context.add(User("admin@altoquepay.pe", "hashed:clave-admin", Role.SYSTEM_ADMIN))

    await context.service.sign_in(SignInCommand("admin@altoquepay.pe", "clave-admin"))

    assert context.unit_of_work.commits == 0


async def test_changing_the_temporary_password_returns_an_unblocked_token(context):
    customer = await context.add(User.customer(Dni("01234567"), "hashed:Temporal7k"))

    signed_in = await context.service.change_password(
        ChangePasswordCommand(customer.id, "Temporal7k", "mi-clave-segura")
    )

    stored = context.users.stored[customer.id]
    assert (stored.password_hash, stored.must_change_password) == ("hashed:mi-clave-segura", False)
    assert signed_in.user.must_change_password is False
    assert context.tokens.issued[-1].must_change_password is False
    assert context.unit_of_work.commits == 1


async def test_wrong_current_password_is_rejected_on_its_field(context):
    customer = await context.add(User.customer(Dni("01234567"), "hashed:Temporal7k"))

    with pytest.raises(BusinessError) as error:
        await context.service.change_password(
            ChangePasswordCommand(customer.id, "Temporal8k", "mi-clave-segura")
        )

    assert (error.value.code, error.value.field) == (
        "INVALID_CURRENT_PASSWORD",
        "current_password",
    )
    assert context.unit_of_work.commits == 0


@pytest.mark.parametrize(
    ("new_password", "code"),
    [("corta", "INVALID_PASSWORD"), ("Temporal7k", "PASSWORD_UNCHANGED")],
)
async def test_new_password_must_be_valid_and_different(context, new_password, code):
    customer = await context.add(User.customer(Dni("01234567"), "hashed:Temporal7k"))

    with pytest.raises(BusinessError) as error:
        await context.service.change_password(
            ChangePasswordCommand(customer.id, "Temporal7k", new_password)
        )

    assert (error.value.code, error.value.field) == (code, "new_password")
    assert context.users.stored[customer.id].password_hash == "hashed:Temporal7k"
