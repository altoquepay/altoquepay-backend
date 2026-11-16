"""Tests for the store repository against the migrated PostgreSQL database.

No test commits, so every store added here disappears when its session closes.
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.shared.domain.value_objects import CreditConditions, Rate, Ruc
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.stores.domain.model.aggregates.store import Store, StoreStatus
from app.stores.infrastructure.persistence.store_repository_impl import StoreRepositoryImpl

RUC = Ruc("20999999901")


@pytest.fixture
async def repository():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield StoreRepositoryImpl(unit_of_work.session)


async def test_adding_a_store_sets_its_id_and_registration_time(repository):
    store = Store.register("Bodega La Esquina", RUC)

    await repository.add(store)

    assert store.id is not None and store.registered_at is not None
    assert await repository.find_by_id(store.id) == store
    assert await repository.exists_by_ruc(RUC)
    assert not await repository.exists_by_ruc(Ruc("20999999902"))


async def test_update_saves_the_profile_and_status(repository):
    store = Store.register("Bodega La Esquina", RUC)
    await repository.add(store)
    conditions = CreditConditions(20, 26, Rate.from_percent(Decimal("50.5")), Rate(Decimal(0)), 8)

    store.update_profile("Bodega Don Lucho", "Av. Los Jardines 123", "987654321", conditions)
    store.deactivate()
    await repository.update(store)

    stored = await repository.find_by_id(store.id)
    assert (stored.business_name, stored.status) == ("Bodega Don Lucho", StoreStatus.INACTIVE)
    assert stored.default_conditions == conditions


async def test_lists_the_newest_store_first_with_the_total(repository):
    older = Store.register("Bodega Antigua", RUC)
    newer = Store.register("Bodega Nueva", Ruc("20999999902"))
    await repository.add(older)
    await repository.add(newer)

    stores, total = await repository.list_page(offset=0, size=2)

    assert [store.id for store in stores] == [newer.id, older.id]
    assert total >= 2


async def test_database_rejects_a_repeated_ruc(repository):
    await repository.add(Store.register("Bodega La Esquina", RUC))
    with pytest.raises(IntegrityError):
        await repository.add(Store.register("Otra Bodega", RUC))
