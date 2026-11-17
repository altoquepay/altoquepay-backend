from app.customers.application.ports.customer_users import CustomerUsers
from app.iam.interfaces.acl.iam_facade import IamFacade


class ExternalUsers(CustomerUsers):
    def __init__(self, iam_facade: IamFacade) -> None:
        self._iam_facade = iam_facade

    async def find_user_id(self, username: str) -> int | None:
        user = await self._iam_facade.find_user_by_username(username)
        return user.user_id if user else None

    async def create(self, dni: str) -> int:
        return await self._iam_facade.create_customer_user(dni)
