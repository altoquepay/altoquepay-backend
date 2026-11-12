from datetime import date

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap
from app.regulation.domain.repositories.bcrp_cap_repository import BcrpCapRepository
from app.regulation.infrastructure.persistence.mappers import to_domain, to_model
from app.regulation.infrastructure.persistence.models import BcrpCapModel


class BcrpCapRepositoryImpl(BcrpCapRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_in_force(self, on_date: date) -> BcrpCap | None:
        model = await self._session.scalar(
            select(BcrpCapModel).where(
                BcrpCapModel.valid_from <= on_date, BcrpCapModel.valid_to >= on_date
            )
        )
        return to_domain(model) if model else None

    async def exists_overlapping(self, valid_from: date, valid_to: date) -> bool:
        overlapping = exists().where(
            BcrpCapModel.valid_from <= valid_to, BcrpCapModel.valid_to >= valid_from
        )
        return bool(await self._session.scalar(select(overlapping)))

    async def list_all(self) -> list[BcrpCap]:
        models = await self._session.scalars(
            select(BcrpCapModel).order_by(BcrpCapModel.valid_from.desc())
        )
        return [to_domain(model) for model in models]

    async def add(self, cap: BcrpCap) -> None:
        model = to_model(cap)
        self._session.add(model)
        await self._session.flush()
        cap.id = model.id
