from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.stores.application.ports.customer_counter import CustomerCounter


class ExternalCustomers(CustomerCounter):
    def __init__(self, customers_facade: CustomersFacade) -> None:
        self._customers_facade = customers_facade

    async def count(self, store_id: int) -> int:
        return await self._customers_facade.count_by_store(store_id)
