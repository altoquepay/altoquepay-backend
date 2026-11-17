from datetime import datetime

from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.iam.application.ports.customer_directory import CustomerDirectory


class ExternalCustomers(CustomerDirectory):
    def __init__(self, customers_facade: CustomersFacade) -> None:
        self._customers_facade = customers_facade

    async def get_customer_id(self, user_id: int) -> int:
        return await self._customers_facade.get_customer_id_by_user(user_id)

    async def redeem_access_code(self, dni: str, code: str, now: datetime) -> int:
        return await self._customers_facade.redeem_access_code(dni, code, now)
