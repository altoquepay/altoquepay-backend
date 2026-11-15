"""In-memory stand-ins for the ports of the stores use cases, for tests without a database."""

from dataclasses import replace
from datetime import UTC, datetime

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Ruc
from app.stores.application.ports.store_administrators import StoreAdministrators
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.repositories.store_repository import StoreRepository


class InMemoryStores(StoreRepository):
    def __init__(self) -> None:
        self.stored: dict[int, Store] = {}

    async def find_by_id(self, store_id: int) -> Store | None:
        store = self.stored.get(store_id)
        return replace(store) if store else None

    async def exists_by_ruc(self, ruc: Ruc) -> bool:
        return any(store.ruc == ruc for store in self.stored.values())

    async def list_page(self, offset: int, size: int) -> tuple[list[Store], int]:
        newest_first = sorted(self.stored.values(), key=lambda store: -(store.id or 0))
        return [replace(store) for store in newest_first[offset : offset + size]], len(newest_first)

    async def add(self, store: Store) -> None:
        store.id = len(self.stored) + 1
        store.registered_at = datetime(2026, 11, 12, tzinfo=UTC)
        self.stored[store.id] = replace(store)

    async def update(self, store: Store) -> None:
        assert store.id in self.stored
        self.stored[store.id] = replace(store)


class RecordingAdministrators(StoreAdministrators):
    def __init__(self, taken_email: str | None = None) -> None:
        self.taken_email = taken_email
        self.created: list[tuple[str, int]] = []

    async def create(self, email: str, full_name: str, password: str, store_id: int) -> int:
        if email == self.taken_email:
            raise BusinessError(
                "EMAIL_TAKEN", "The email is already registered.", "email", None, 409
            )
        self.created.append((email, store_id))
        return len(self.created)
