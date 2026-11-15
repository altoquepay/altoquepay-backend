from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.domain.value_objects import Ruc
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.repositories.store_repository import StoreRepository
from app.stores.infrastructure.persistence.mappers import copy_to_model, to_domain
from app.stores.infrastructure.persistence.models import StoreModel


class StoreRepositoryImpl(StoreRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, store_id: int) -> Store | None:
        model = await self._session.get(StoreModel, store_id)
        return to_domain(model) if model else None

    async def exists_by_ruc(self, ruc: Ruc) -> bool:
        return bool(await self._session.scalar(select(exists().where(StoreModel.ruc == ruc.value))))

    async def list_page(self, offset: int, size: int) -> tuple[list[Store], int]:
        total = await self._session.scalar(select(func.count()).select_from(StoreModel))
        models = await self._session.scalars(
            select(StoreModel)
            .order_by(StoreModel.registered_at.desc(), StoreModel.id.desc())
            .offset(offset)
            .limit(size)
        )
        return [to_domain(model) for model in models], total or 0

    async def add(self, store: Store) -> None:
        model = copy_to_model(store, StoreModel())
        self._session.add(model)
        await self._session.flush()
        # The database sets the registration time, so read it back.
        await self._session.refresh(model, ["registered_at"])
        store.id = model.id
        store.registered_at = model.registered_at

    async def update(self, store: Store) -> None:
        if store.id is None:
            raise ValueError("Only a stored store can be updated.")
        model = await self._session.get_one(StoreModel, store.id)
        copy_to_model(store, model)
        await self._session.flush()
