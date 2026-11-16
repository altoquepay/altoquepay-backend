from dataclasses import dataclass

from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.model.aggregates.store_customer import StoreCustomer
from app.customers.domain.repositories.customer_repository import CustomerRepository
from app.customers.domain.repositories.store_customer_repository import (
    AccountFilter,
    StoreCustomerRepository,
)
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni

PERSON_HAS_ACCOUNT = "PERSON_HAS_ACCOUNT"


@dataclass(frozen=True)
class CustomerAccount:
    account: StoreCustomer
    customer: Customer


@dataclass(frozen=True)
class PersonLookup:
    """account_id is the person's account in the asking store, if there is one.

    notice is PERSON_HAS_ACCOUNT when the person already buys in another store, so the store
    knows it is opening an account for someone who already has a user.
    """

    customer: Customer
    account_id: int | None
    notice: str | None


def account_not_found() -> BusinessError:
    return BusinessError("NOT_FOUND", "The customer account does not exist.", status=404)


class AccountQueryService:
    def __init__(self, customers: CustomerRepository, accounts: StoreCustomerRepository) -> None:
        self._customers = customers
        self._accounts = accounts

    async def get(self, store_id: int, account_id: int) -> CustomerAccount:
        """Raise NOT_FOUND (404) for an account of another store, as if it did not exist."""
        account = await self._accounts.find_by_id(account_id)
        if account is None or account.store_id != store_id:
            raise account_not_found()
        customer = await self._customers.find_by_id(account.customer_id)
        if customer is None:
            raise account_not_found()
        return CustomerAccount(account, customer)

    async def list_page(
        self, store_id: int, account_filter: AccountFilter, offset: int, size: int
    ) -> tuple[list[CustomerAccount], int]:
        rows, total = await self._accounts.list_page(store_id, account_filter, offset, size)
        return [CustomerAccount(account, customer) for account, customer in rows], total

    async def lookup(self, store_id: int, dni: Dni) -> PersonLookup:
        """Find a person by DNI. Raise NOT_FOUND (404) if nobody has it yet."""
        customer = await self._customers.find_by_dni(dni)
        if customer is None or customer.id is None:
            raise BusinessError("NOT_FOUND", "No customer has this DNI.", status=404)
        accounts = await self._accounts.list_by_customer(customer.id)
        own = next((account for account in accounts if account.store_id == store_id), None)
        in_other_store = any(account.store_id != store_id for account in accounts)
        return PersonLookup(
            customer,
            own.id if own else None,
            PERSON_HAS_ACCOUNT if in_other_store else None,
        )
