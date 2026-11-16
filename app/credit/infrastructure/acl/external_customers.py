from app.credit.application.ports.credit_accounts import AccountTerms, CreditAccounts
from app.customers.interfaces.acl.customers_facade import CustomersFacade
from app.shared.domain.value_objects import Money, Rate

ACTIVE_ACCOUNT_STATUS = "ACTIVE"


class ExternalCustomers(CreditAccounts):
    def __init__(self, customers_facade: CustomersFacade) -> None:
        self._customers_facade = customers_facade

    async def lock_and_read(self, account_id: int) -> AccountTerms:
        await self._customers_facade.lock_account(account_id)
        terms = await self._customers_facade.get_credit_terms(account_id)
        return AccountTerms(
            store_id=terms.store_id,
            credit_limit=Money(terms.credit_limit),
            tea=Rate.from_percent(terms.tea),
            late_tea=Rate.from_percent(terms.late_tea),
            max_weeks=terms.max_weeks,
            is_active=terms.status == ACTIVE_ACCOUNT_STATUS,
        )
