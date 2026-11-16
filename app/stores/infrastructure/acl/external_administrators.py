from app.iam.interfaces.acl.iam_facade import IamFacade
from app.stores.application.ports.store_administrators import StoreAdministrators


class ExternalAdministrators(StoreAdministrators):
    def __init__(self, iam_facade: IamFacade) -> None:
        self._iam_facade = iam_facade

    async def create(self, email: str, full_name: str, password: str, store_id: int) -> int:
        return await self._iam_facade.create_store_admin(email, full_name, password, store_id)
