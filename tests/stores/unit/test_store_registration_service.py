"""Tests for the public store registration (E2) without a database."""

import pytest

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Ruc
from app.stores.application.command_services.store_registration_service import (
    StoreRegistrationService,
)
from app.stores.domain.model.commands.register_store_command import RegisterStoreCommand
from tests.iam.fakes import CountingUnitOfWork
from tests.stores.fakes import InMemoryStores, RecordingAdministrators

COMMAND = RegisterStoreCommand(
    "Bodega La Esquina", Ruc("10456781234"), "Rosa Quispe", "rosa@bodega.pe", "mi-clave-segura"
)


@pytest.fixture
def stores():
    return InMemoryStores()


@pytest.fixture
def unit_of_work():
    return CountingUnitOfWork()


async def test_store_and_administrator_are_saved_in_one_commit(stores, unit_of_work):
    administrators = RecordingAdministrators()
    service = StoreRegistrationService(stores, administrators, unit_of_work)

    store = await service.register(COMMAND)

    assert administrators.created == [("rosa@bodega.pe", store.id)]
    assert unit_of_work.commits == 1


async def test_nothing_is_committed_when_the_administrator_is_not_valid(stores, unit_of_work):
    service = StoreRegistrationService(
        stores, RecordingAdministrators(taken_email="rosa@bodega.pe"), unit_of_work
    )

    with pytest.raises(BusinessError) as error:
        await service.register(COMMAND)

    assert error.value.code == "EMAIL_TAKEN"
    assert unit_of_work.commits == 0


async def test_repeated_ruc_is_rejected(stores, unit_of_work):
    service = StoreRegistrationService(stores, RecordingAdministrators(), unit_of_work)
    await service.register(COMMAND)

    with pytest.raises(BusinessError) as error:
        await service.register(COMMAND)

    assert (error.value.code, error.value.field, error.value.status) == ("RUC_TAKEN", "ruc", 409)
    assert unit_of_work.commits == 1


def test_command_never_shows_the_password():
    assert "mi-clave-segura" not in repr(COMMAND)
