from app.iam.domain.model.aggregates.user import User
from app.iam.domain.repositories.user_repository import UserRepository
from app.shared.domain.errors import BusinessError


class UserQueryService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def get_by_id(self, user_id: int) -> User:
        user = await self._users.find_by_id(user_id)
        if user is None:
            raise BusinessError("NOT_FOUND", "The user does not exist.", status=404)
        return user
