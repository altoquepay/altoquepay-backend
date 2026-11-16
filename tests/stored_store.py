"""A store saved in the session of a test, since users.store_id references stores."""

from app.shared.domain.value_objects import Ruc
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.stores.domain.model.aggregates.store import Store
from app.stores.infrastructure.persistence.store_repository_impl import StoreRepositoryImpl


async def add_store(unit_of_work: UnitOfWork, ruc: str = "20999999990") -> Store:
    """Flush a new active store without committing it, and return it with its id."""
    store = Store.register("Bodega de Prueba", Ruc(ruc))
    await StoreRepositoryImpl(unit_of_work.session).add(store)
    return store
