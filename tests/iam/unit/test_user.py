"""Tests for the user aggregate and the values it is built from."""

import pytest

from app.iam.domain.model.aggregates.password_reset_token import PasswordResetToken
from app.iam.domain.model.aggregates.user import User, normalize_username
from app.iam.domain.model.value_objects.email import Email
from app.iam.domain.model.value_objects.password import ensure_valid_password
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni, Role


def test_email_is_stored_in_lowercase_without_spaces():
    assert Email("  Rosa@Bodega.PE ").value == "rosa@bodega.pe"


@pytest.mark.parametrize("invalid_email", ["rosa", "rosa@bodega", "ro sa@bodega.pe", ""])
def test_invalid_email_is_rejected(invalid_email):
    with pytest.raises(BusinessError) as error:
        Email(invalid_email)
    assert (error.value.code, error.value.field) == ("INVALID_EMAIL", "email")


@pytest.mark.parametrize("password", ["1234567", "x" * 129])
def test_password_outside_the_allowed_length_is_rejected_on_its_field(password):
    with pytest.raises(BusinessError) as error:
        ensure_valid_password(password, field="new_password")
    assert (error.value.code, error.value.field) == ("INVALID_PASSWORD", "new_password")


def test_passwords_of_8_and_128_characters_are_allowed():
    ensure_valid_password("x" * 8)
    ensure_valid_password("x" * 128)


def test_store_admin_belongs_to_a_store_and_keeps_the_password_chosen():
    user = User.store_admin(Email("rosa@bodega.pe"), " Rosa Quispe ", "hash", store_id=3)

    assert (user.username, user.full_name, user.role) == (
        "rosa@bodega.pe",
        "Rosa Quispe",
        Role.STORE_ADMIN,
    )
    assert (user.store_id, user.must_change_password, user.is_active) == (3, False, True)


@pytest.mark.parametrize("full_name", ["   ", "x" * 151])
def test_store_admin_needs_a_full_name(full_name):
    with pytest.raises(BusinessError) as error:
        User.store_admin(Email("rosa@bodega.pe"), full_name, "hash", store_id=3)
    assert (error.value.code, error.value.field) == ("INVALID_FULL_NAME", "full_name")


def test_customer_signs_in_with_the_dni_and_has_no_temporary_password():
    user = User.customer(Dni("01234567"), "hash")

    assert (user.username, user.role, user.store_id) == ("01234567", Role.CUSTOMER, None)
    assert not user.must_change_password


def test_only_a_store_admin_has_a_store():
    with pytest.raises(ValueError):
        User("01234567", "hash", Role.CUSTOMER, store_id=3)
    with pytest.raises(ValueError):
        User("rosa@bodega.pe", "hash", Role.STORE_ADMIN)


def test_changing_the_password_lifts_the_temporary_password_block():
    user = User.system_admin(Email("admin@altoquepay.pe"), "temporary")
    assert user.must_change_password

    user.change_password("chosen")

    assert (user.password_hash, user.must_change_password) == ("chosen", False)


def test_every_password_change_gets_a_new_version():
    user = User.customer(Dni("01234567"), "nobody knows it")

    user.change_password("chosen")
    user.change_password("chosen again")

    assert user.password_version == 2


def test_usernames_are_compared_in_lowercase():
    assert normalize_username(" Rosa@Bodega.pe ") == "rosa@bodega.pe"
    assert normalize_username("01234567") == "01234567"


def test_reset_token_works_once_and_until_it_expires():
    from datetime import UTC, datetime, timedelta

    now = datetime(2026, 11, 12, 15, tzinfo=UTC)
    token = PasswordResetToken(user_id=1, token_hash="h", expires_at=now + timedelta(minutes=30))

    assert token.is_usable(now)
    assert not token.is_usable(now + timedelta(minutes=30))
    token.use(now)
    assert not token.is_usable(now)
