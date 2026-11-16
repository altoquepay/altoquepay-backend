"""The only way other bounded contexts may reach the customers context.

An account is a row of store_customers: the conditions of one person in one store.
Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from decimal import Decimal

from app.customers.infrastructure.persistence.customer_repository_impl import (
    CustomerRepositoryImpl,
)
from app.customers.infrastructure.persistence.store_customer_repository_impl import (
    StoreCustomerRepositoryImpl,
)
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class CreditTerms:
    account_id: int
    store_id: int
    customer_id: int
    credit_limit: Decimal
    tea: Decimal
    late_tea: Decimal
    cutoff_day: int
    payment_day: int
    max_weeks: int
    status: str


@dataclass(frozen=True)
class AccountSummary:
    account_id: int
    store_id: int
    status: str


def account_not_found() -> BusinessError:
    return BusinessError("NOT_FOUND", "The customer account does not exist.", status=404)


class CustomersFacade:
    """Never commits: the use case of the calling context does, once all its work succeeded."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._accounts = StoreCustomerRepositoryImpl(unit_of_work.session)
        self._customers = CustomerRepositoryImpl(unit_of_work.session)

    async def get_credit_terms(self, account_id: int) -> CreditTerms:
        """Return the conditions of an account. Callers compare its store_id with the token's.

        Raises NOT_FOUND (404) if the account does not exist.
        """
        account = await self._accounts.find_by_id(account_id)
        if account is None or account.id is None:
            raise account_not_found()
        conditions = account.conditions
        return CreditTerms(
            account_id=account.id,
            store_id=account.store_id,
            customer_id=account.customer_id,
            credit_limit=account.credit_limit.amount,
            tea=conditions.tea.percent,
            late_tea=conditions.late_tea.percent,
            cutoff_day=conditions.cutoff_day,
            payment_day=conditions.payment_day,
            max_weeks=conditions.max_weeks,
            status=account.status.value,
        )

    async def lock_account(self, account_id: int) -> None:
        """Lock the account with FOR UPDATE until the transaction ends.

        Call it before reading the credit terms, so two concurrent purchases or payments
        cannot both pass the credit limit check. Raises NOT_FOUND (404) if it does not exist.
        """
        if not await self._accounts.lock(account_id):
            raise account_not_found()

    async def get_accounts_of_person(self, customer_id: int) -> list[AccountSummary]:
        """Return the active and inactive accounts of a person in every store."""
        return [
            AccountSummary(account.id, account.store_id, account.status.value)
            for account in await self._accounts.list_by_customer(customer_id)
            if account.id is not None
        ]

    async def count_by_store(self, store_id: int) -> int:
        """Return the number of active accounts of a store."""
        return await self._accounts.count_active_by_store(store_id)

    async def get_customer_id_by_user(self, user_id: int) -> int:
        """Return the person of a customer user, needed by the login for the customer_id claim.

        Raises NOT_FOUND (404) if the user is not a registered customer.
        """
        customer_id = await self._customers.find_id_by_user(user_id)
        if customer_id is None:
            raise BusinessError("NOT_FOUND", "The customer does not exist.", status=404)
        return customer_id
