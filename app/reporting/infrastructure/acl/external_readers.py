from datetime import date
from decimal import Decimal

from app.billing.interfaces.acl.billing_facade import BillingFacade, CycleStatement, PaymentSummary
from app.credit.interfaces.acl.credit_facade import (
    CreditFacade,
    InstallmentSummary,
    PurchaseSummary,
)
from app.customers.interfaces.acl.customers_facade import (
    AccountSummary,
    CreditTerms,
    CustomersFacade,
)
from app.regulation.interfaces.acl.regulation_facade import CurrentCap, RegulationFacade
from app.reporting.application.ports.readers import (
    BillingReader,
    CreditReader,
    CustomerAccounts,
    RateCaps,
    StoreDirectory,
)
from app.shared.domain.errors import BusinessError
from app.stores.interfaces.acl.stores_facade import StoresFacade, StoreSummary


class ExternalCustomers(CustomerAccounts):
    def __init__(self, customers_facade: CustomersFacade) -> None:
        self._facade = customers_facade

    async def customer_of_user(self, user_id: int) -> int:
        return await self._facade.get_customer_id_by_user(user_id)

    async def accounts_of_person(self, customer_id: int) -> list[AccountSummary]:
        return await self._facade.get_accounts_of_person(customer_id)

    async def accounts_of_store(self, store_id: int) -> list[AccountSummary]:
        return await self._facade.list_accounts_of_store(store_id)

    async def terms(self, account_id: int) -> CreditTerms:
        return await self._facade.get_credit_terms(account_id)

    async def active_count(self, store_id: int) -> int:
        return await self._facade.count_by_store(store_id)


class ExternalStores(StoreDirectory):
    def __init__(self, stores_facade: StoresFacade) -> None:
        self._facade = stores_facade

    async def summary(self, store_id: int) -> StoreSummary:
        return await self._facade.get_store_status(store_id)


class ExternalCredit(CreditReader):
    def __init__(self, credit_facade: CreditFacade) -> None:
        self._facade = credit_facade

    async def outstanding_principal(self, account_id: int) -> Decimal:
        return await self._facade.get_outstanding_principal(account_id)

    async def installments_due(
        self, account_id: int, from_date: date, to_date: date
    ) -> list[InstallmentSummary]:
        return await self._facade.get_installments_due(account_id, from_date, to_date)

    async def purchases(self, account_id: int) -> list[PurchaseSummary]:
        return await self._facade.list_purchases(account_id)

    async def purchase(self, purchase_id: int) -> PurchaseSummary:
        return await self._facade.get_purchase(purchase_id)


class ExternalBilling(BillingReader):
    def __init__(self, billing_facade: BillingFacade) -> None:
        self._facade = billing_facade

    async def statement(self, account_id: int, year: int, month: int) -> CycleStatement | None:
        return await self._facade.get_cycle_statement(account_id, year, month)

    async def payments(self, account_id: int) -> list[PaymentSummary]:
        return await self._facade.list_payments(account_id)


class ExternalRateCaps(RateCaps):
    def __init__(self, regulation_facade: RegulationFacade) -> None:
        self._facade = regulation_facade

    async def in_force(self, on_date: date) -> CurrentCap | None:
        try:
            return await self._facade.get_current_cap(on_date)
        except BusinessError as error:
            # The dashboard still loads without a cap; it shows that one must be registered.
            if error.code == "NO_BCRP_CAP_IN_FORCE":
                return None
            raise
