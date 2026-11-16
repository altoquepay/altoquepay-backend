"""What a customer sees of their own accounts. The person always comes from the token's user."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.billing.interfaces.acl.billing_facade import CycleStatement
from app.credit.interfaces.acl.credit_facade import InstallmentSummary, PurchaseSummary
from app.customers.interfaces.acl.customers_facade import AccountSummary, CreditTerms
from app.reporting.application.ports.readers import (
    BillingReader,
    CreditReader,
    CustomerAccounts,
    StoreDirectory,
)
from app.shared.domain.errors import BusinessError
from app.stores.interfaces.acl.stores_facade import StoreSummary

# Wide enough to cover every installment an account can have.
FIRST_DAY = date(1, 1, 1)
LAST_DAY = date(9999, 12, 31)


@dataclass(frozen=True)
class CustomerStore:
    account: AccountSummary
    store: StoreSummary


@dataclass(frozen=True)
class AccountOverview:
    store: StoreSummary
    terms: CreditTerms
    outstanding_principal: Decimal
    installments: list[InstallmentSummary]

    @property
    def available_credit(self) -> Decimal:
        return max(self.terms.credit_limit - self.outstanding_principal, Decimal("0.00"))


@dataclass(frozen=True)
class PurchaseSchedule:
    """installments are the ones still to pay; paid ones are not listed by credit's facade."""

    purchase: PurchaseSummary
    installments: list[InstallmentSummary]


def not_found(what: str) -> BusinessError:
    return BusinessError("NOT_FOUND", f"The {what} does not exist.", status=404)


class CustomerPortalService:
    def __init__(
        self,
        accounts: CustomerAccounts,
        stores: StoreDirectory,
        credit: CreditReader,
        billing: BillingReader,
    ) -> None:
        self._accounts = accounts
        self._stores = stores
        self._credit = credit
        self._billing = billing

    async def my_stores(self, user_id: int) -> list[CustomerStore]:
        """Return every store where the customer has an account, active or not."""
        customer_id = await self._accounts.customer_of_user(user_id)
        return [
            CustomerStore(account, await self._stores.summary(account.store_id))
            for account in await self._accounts.accounts_of_person(customer_id)
        ]

    async def overview(self, user_id: int, store_id: int) -> AccountOverview:
        account = await self._account_in(user_id, store_id)
        return AccountOverview(
            store=await self._stores.summary(store_id),
            terms=await self._accounts.terms(account.account_id),
            outstanding_principal=await self._credit.outstanding_principal(account.account_id),
            installments=await self._credit.installments_due(
                account.account_id, FIRST_DAY, LAST_DAY
            ),
        )

    async def statement(self, user_id: int, store_id: int, year: int, month: int) -> CycleStatement:
        account = await self._account_in(user_id, store_id)
        statement = await self._billing.statement(account.account_id, year, month)
        if statement is None:
            raise not_found("cycle of that month")
        return statement

    async def purchases(self, user_id: int, store_id: int) -> list[PurchaseSummary]:
        account = await self._account_in(user_id, store_id)
        return await self._credit.purchases(account.account_id)

    async def schedule(self, user_id: int, store_id: int, purchase_id: int) -> PurchaseSchedule:
        account = await self._account_in(user_id, store_id)
        purchase = await self._credit.purchase(purchase_id)
        if purchase.account_id != account.account_id:
            raise not_found("purchase")
        pending = await self._credit.installments_due(account.account_id, FIRST_DAY, LAST_DAY)
        return PurchaseSchedule(
            purchase, [i for i in pending if i.purchase_id == purchase.purchase_id]
        )

    async def _account_in(self, user_id: int, store_id: int) -> AccountSummary:
        """Return the customer's account in the store; another store's data is never reached."""
        customer_id = await self._accounts.customer_of_user(user_id)
        for account in await self._accounts.accounts_of_person(customer_id):
            if account.store_id == store_id:
                return account
        raise not_found("store")
