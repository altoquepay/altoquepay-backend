"""Tests for the stores facade against the migrated PostgreSQL database."""

from decimal import Decimal

import pytest

from app.shared.domain.errors import BusinessError
from app.stores.interfaces.acl.stores_facade import DefaultConditions, StoresFacade, StoreSummary
from tests.stored_store import add_store


async def test_status_of_a_store(unit_of_work):
    store = await add_store(unit_of_work)

    summary = await StoresFacade(unit_of_work).get_store_status(store.id)

    assert summary == StoreSummary(store.id, "Bodega de Prueba", "ACTIVE")


async def test_default_conditions_are_percentages(unit_of_work):
    store = await add_store(unit_of_work)

    conditions = await StoresFacade(unit_of_work).get_default_conditions(store.id)

    assert conditions == DefaultConditions(10, 15, Decimal("40"), Decimal("60"), 4)


@pytest.mark.parametrize("method", ["get_store_status", "get_default_conditions"])
async def test_unknown_store_is_not_found(unit_of_work, method):
    with pytest.raises(BusinessError) as error:
        await getattr(StoresFacade(unit_of_work), method)(999999)

    assert (error.value.code, error.value.status) == ("NOT_FOUND", 404)
