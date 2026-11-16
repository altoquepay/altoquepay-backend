from app.billing.application.ports.account_directory import AccountDirectory, AccountInfo
from app.customers.interfaces.acl.customers_facade import CustomersFacade


class ExternalAccounts(AccountDirectory):
    def __init__(self, customers_facade: CustomersFacade) -> None:
        self._customers_facade = customers_facade

    async def get_account(self, account_id: int) -> AccountInfo:
        terms = await self._customers_facade.get_credit_terms(account_id)
        return AccountInfo(terms.store_id, terms.cutoff_day, terms.payment_day)

    async def lock(self, account_id: int) -> None:
        await self._customers_facade.lock_account(account_id)
