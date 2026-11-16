from app.billing.application.ports.account_directory import AccountDirectory, CycleDays
from app.customers.interfaces.acl.customers_facade import CustomersFacade


class ExternalAccounts(AccountDirectory):
    def __init__(self, customers_facade: CustomersFacade) -> None:
        self._customers_facade = customers_facade

    async def get_cycle_days(self, account_id: int) -> CycleDays:
        terms = await self._customers_facade.get_credit_terms(account_id)
        return CycleDays(terms.cutoff_day, terms.payment_day)
