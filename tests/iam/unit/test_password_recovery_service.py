"""Tests for resetting a forgotten password through an emailed link."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.iam.application.command_services.password_recovery_service import (
    PasswordRecoveryService,
    hash_reset_token,
)
from app.iam.domain.model.aggregates.user import User
from app.iam.domain.model.commands.reset_forgotten_password_command import (
    ResetForgottenPasswordCommand,
)
from app.iam.domain.model.value_objects.email import Email
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni
from tests.iam.fakes import (
    CountingUnitOfWork,
    InMemoryResetTokens,
    InMemoryUsers,
    PlainHasher,
    RecordingNotifier,
)


class Context:
    def __init__(self, notifier: RecordingNotifier | None = None) -> None:
        self.users = InMemoryUsers()
        self.reset_tokens = InMemoryResetTokens()
        self.notifier = notifier or RecordingNotifier()
        self.unit_of_work = CountingUnitOfWork()
        self.service = PasswordRecoveryService(
            self.users,
            self.reset_tokens,
            PlainHasher(),
            self.notifier,
            self.unit_of_work,  # type: ignore[arg-type]
            token_minutes=30,
            frontend_url="https://app.altoquepay.pe/",
        )

    async def add_admin(self) -> User:
        admin = User.store_admin(Email("rosa@bodega.pe"), "Rosa", "hashed:olvidada", store_id=3)
        await self.users.add(admin)
        return admin

    def token_of_last_link(self) -> str:
        link = self.notifier.sent[-1][1]
        return parse_qs(urlparse(link).query)["token"][0]


@pytest.fixture
def context():
    return Context()


async def test_admin_gets_a_link_to_the_frontend_with_a_token_kept_only_as_a_hash(context):
    admin = await context.add_admin()

    await context.service.request_reset("Rosa@Bodega.pe")

    email, link = context.notifier.sent[0]
    assert email == "rosa@bodega.pe"
    assert link.startswith("https://app.altoquepay.pe/reset-password?token=")
    stored_token = context.reset_tokens.stored[0]
    assert stored_token.user_id == admin.id
    assert stored_token.token_hash == hash_reset_token(context.token_of_last_link())
    assert stored_token.token_hash != context.token_of_last_link()
    assert context.unit_of_work.commits == 1


async def test_link_expires_after_the_configured_minutes(context):
    await context.add_admin()

    before = datetime.now(UTC)
    await context.service.request_reset("rosa@bodega.pe")

    expires_at = context.reset_tokens.stored[0].expires_at
    assert before + timedelta(minutes=30) <= expires_at <= datetime.now(UTC) + timedelta(minutes=30)


async def test_unknown_email_and_customers_get_no_email_and_no_error(context):
    await context.users.add(User.customer(Dni("01234567"), "hashed:x"))

    await context.service.request_reset("nadie@bodega.pe")
    await context.service.request_reset("01234567")

    assert context.notifier.sent == []
    assert context.reset_tokens.stored == []


async def test_failed_email_does_not_reveal_that_the_account_exists():
    context = Context(RecordingNotifier(fails=True))
    await context.add_admin()

    await context.service.request_reset("rosa@bodega.pe")

    assert len(context.reset_tokens.stored) == 1


async def test_token_sets_the_new_password_once(context):
    admin = await context.add_admin()
    await context.service.request_reset("rosa@bodega.pe")
    token = context.token_of_last_link()

    await context.service.reset(ResetForgottenPasswordCommand(token, "nueva-clave"))

    assert context.users.stored[admin.id].password_hash == "hashed:nueva-clave"
    with pytest.raises(BusinessError) as error:
        await context.service.reset(ResetForgottenPasswordCommand(token, "otra-clave"))
    assert (error.value.code, error.value.field) == ("INVALID_RESET_TOKEN", "token")


async def test_using_a_link_disables_the_older_ones(context):
    await context.add_admin()
    await context.service.request_reset("rosa@bodega.pe")
    older_token = context.token_of_last_link()
    await context.service.request_reset("rosa@bodega.pe")

    await context.service.reset(
        ResetForgottenPasswordCommand(context.token_of_last_link(), "nueva-clave")
    )

    with pytest.raises(BusinessError):
        await context.service.reset(ResetForgottenPasswordCommand(older_token, "otra-clave"))


async def test_expired_or_unknown_token_is_rejected(context):
    await context.add_admin()
    await context.service.request_reset("rosa@bodega.pe")
    context.reset_tokens.stored[0].expires_at = datetime.now(UTC) - timedelta(seconds=1)

    for token in (context.token_of_last_link(), "made-up-token"):
        with pytest.raises(BusinessError) as error:
            await context.service.reset(ResetForgottenPasswordCommand(token, "nueva-clave"))
        assert error.value.code == "INVALID_RESET_TOKEN"


async def test_reset_also_lifts_a_temporary_password_block(context):
    admin = await context.add_admin()
    stored = context.users.stored[admin.id]
    stored.must_change_password = True
    await context.service.request_reset("rosa@bodega.pe")

    await context.service.reset(
        ResetForgottenPasswordCommand(context.token_of_last_link(), "nueva-clave")
    )

    assert context.users.stored[admin.id].must_change_password is False


async def test_invalid_new_password_keeps_the_token_usable(context):
    await context.add_admin()
    await context.service.request_reset("rosa@bodega.pe")

    with pytest.raises(BusinessError) as error:
        await context.service.reset(
            ResetForgottenPasswordCommand(context.token_of_last_link(), "corta")
        )

    assert (error.value.code, error.value.field) == ("INVALID_PASSWORD", "new_password")
    assert context.reset_tokens.stored[0].used_at is None
