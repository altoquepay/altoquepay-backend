from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.iam.domain.model.aggregates.user import User
from app.iam.domain.repositories.user_repository import UserRepository
from app.iam.infrastructure.persistence.mappers import copy_to_model, to_domain
from app.iam.infrastructure.persistence.models import UserModel


class UserRepositoryImpl(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return to_domain(model) if model else None

    async def find_by_username(self, username: str) -> User | None:
        model = await self._session.scalar(select(UserModel).where(UserModel.username == username))
        return to_domain(model) if model else None

    async def exists_by_username(self, username: str) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(UserModel.username == username)))
        )

    async def add(self, user: User) -> None:
        model = copy_to_model(user, UserModel())
        self._session.add(model)
        await self._session.flush()
        user.id = model.id

    async def update(self, user: User) -> None:
        if user.id is None:
            raise ValueError("Only a stored user can be updated.")
        model = await self._session.get_one(UserModel, user.id)
        copy_to_model(user, model)
        await self._session.flush()
