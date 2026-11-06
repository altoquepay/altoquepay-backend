"""The only way other bounded contexts may reach the customers context.

An account is a row of store_customers: the conditions of one person in one store.
Rates are percentages, as stored: 75% is Decimal("75.0000000").
"""

from dataclasses import dataclass
from decimal import Decimal

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


class CustomersFacade:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def get_credit_terms(self, account_id: int) -> CreditTerms:
        """Return the conditions of an account. Callers compare its store_id with the token's."""
        raise NotImplementedError

    async def lock_account(self, account_id: int) -> None:
        """Lock the account with FOR UPDATE until the transaction ends.

        Call it before reading the credit terms, so two concurrent purchases or payments
        cannot both pass the credit limit check.
        """
        raise NotImplementedError

    async def get_accounts_of_person(self, customer_id: int) -> list[AccountSummary]:
        """Return the active and inactive accounts of a person in every store."""
        raise NotImplementedError

    async def count_by_store(self, store_id: int) -> int:
        """Return the number of active accounts of a store."""
        raise NotImplementedError

    async def get_customer_id_by_user(self, user_id: int) -> int:
        """Return the person of a customer user, needed by the login for the customer_id claim."""
        raise NotImplementedError
