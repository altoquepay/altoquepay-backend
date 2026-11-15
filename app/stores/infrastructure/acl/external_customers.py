from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.stores.application.ports.customer_counter import CustomerCounter


class ExternalCustomers(CustomerCounter):
    def __init__(self, customers_facade: CustomersFacade) -> None:
        self._customers_facade = customers_facade

    async def count(self, store_id: int) -> int:
        try:
            return await self._customers_facade.count_by_store(store_id)
        except NotImplementedError:
            # shortcut: the customers context is not built yet, so every store shows 0 customers;
            # remove this once CustomersFacade.count_by_store is implemented.
            return 0
