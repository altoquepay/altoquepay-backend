from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.iam.domain.model.aggregates.password_reset_token import PasswordResetToken
from app.iam.domain.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.iam.infrastructure.persistence.mappers import token_to_domain, token_to_model
from app.iam.infrastructure.persistence.models import PasswordResetTokenModel


class PasswordResetTokenRepositoryImpl(PasswordResetTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        model = await self._session.scalar(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        )
        return token_to_domain(model) if model else None

    async def add(self, token: PasswordResetToken) -> None:
        model = token_to_model(token)
        self._session.add(model)
        await self._session.flush()
        token.id = model.id

    async def use_all_of_user(self, user_id: int, now: datetime) -> None:
        await self._session.execute(
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.used_at.is_(None),
            )
            .values(used_at=now)
        )
