from dataclasses import dataclass, replace
from datetime import date

from app.customers.application.ports.customer_users import CustomerCredentials, CustomerUsers
from app.customers.application.ports.rate_cap_checker import RateCapChecker
from app.customers.application.ports.store_defaults import StoreDefaults
from app.customers.application.query_services.account_query_service import (
    AccountQueryService,
    CustomerAccount,
)
from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.model.aggregates.store_customer import StoreCustomer
from app.customers.domain.model.commands.open_account_command import OpenAccountCommand
from app.customers.domain.model.commands.update_account_command import UpdateAccountCommand
from app.customers.domain.repositories.customer_repository import CustomerRepository
from app.customers.domain.repositories.store_customer_repository import StoreCustomerRepository
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import CreditConditions, Rate
from app.shared.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class OpenedAccount:
    """credentials is None when the person already had a user from another store."""

    customer_account: CustomerAccount
    credentials: CustomerCredentials | None


class AccountCommandService:
    def __init__(
        self,
        customers: CustomerRepository,
        accounts: StoreCustomerRepository,
        store_defaults: StoreDefaults,
        rate_caps: RateCapChecker,
        users: CustomerUsers,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._customers = customers
        self._accounts = accounts
        self._store_defaults = store_defaults
        self._rate_caps = rate_caps
        self._users = users
        self._unit_of_work = unit_of_work
        self._query = AccountQueryService(customers, accounts)

    async def open(self, command: OpenAccountCommand, today: date) -> OpenedAccount:
        """Open the store's account for a person, creating the person and their user if new."""
        conditions = await self._conditions_with_defaults(command)
        await self._rate_caps.check(conditions.tea, conditions.late_tea, today)
        customer, credentials = await self._find_or_create_customer(command)
        if customer.id is None:
            raise ValueError("The customer was not stored.")
        # shortcut: two simultaneous openings can both pass this check, and the unique
        # constraint then rejects one with a 500; map IntegrityError to 409 if that ever happens.
        if await self._accounts.find_by_store_and_customer(command.store_id, customer.id):
            raise BusinessError(
                "CUSTOMER_ALREADY_IN_STORE",
                "This person already has an account in the store.",
                field="dni",
                status=409,
            )
        account = StoreCustomer(command.store_id, customer.id, command.credit_limit, conditions)
        await self._accounts.add(account)
        await self._unit_of_work.commit()
        return OpenedAccount(CustomerAccount(account, customer), credentials)

    async def update(self, command: UpdateAccountCommand, today: date) -> CustomerAccount:
        """Replace the person's data and the account terms. The DNI never changes."""
        found = await self._query.get(command.store_id, command.account_id)
        conditions = command.conditions
        await self._rate_caps.check(conditions.tea, conditions.late_tea, today)
        found.customer.update_contact(
            command.first_names, command.last_names, command.phone, command.address
        )
        found.account.update_terms(command.credit_limit, conditions)
        await self._customers.update(found.customer)
        await self._accounts.update(found.account)
        await self._unit_of_work.commit()
        return found

    async def deactivate(self, store_id: int, account_id: int) -> CustomerAccount:
        """Stop new purchases on credit. The person keeps their user and other accounts."""
        found = await self._query.get(store_id, account_id)
        found.account.deactivate()
        await self._accounts.update(found.account)
        await self._unit_of_work.commit()
        return found

    async def reset_password(self, store_id: int, account_id: int) -> CustomerCredentials:
        """Give the customer a new temporary password, for when they forgot theirs."""
        found = await self._query.get(store_id, account_id)
        credentials = await self._users.reset_password(found.customer.user_id)
        await self._unit_of_work.commit()
        return credentials

    async def _conditions_with_defaults(self, command: OpenAccountCommand) -> CreditConditions:
        defaults = await self._store_defaults.get(command.store_id)
        changes = {
            "cutoff_day": command.cutoff_day,
            "payment_day": command.payment_day,
            "tea": Rate.from_percent(command.tea) if command.tea is not None else None,
            "late_tea": Rate.from_percent(command.late_tea)
            if command.late_tea is not None
            else None,
            "max_weeks": command.max_weeks,
        }
        # replace validates the result again, so a mix of given and default days still fails.
        return replace(
            defaults, **{name: value for name, value in changes.items() if value is not None}
        )

    async def _find_or_create_customer(
        self, command: OpenAccountCommand
    ) -> tuple[Customer, CustomerCredentials | None]:
        customer = await self._customers.find_by_dni(command.dni)
        if customer is not None:
            return customer, None
        credentials = None
        user_id = await self._users.find_user_id(command.dni.value)
        if user_id is None:
            credentials = await self._users.create(command.dni.value)
            user_id = credentials.user_id
        customer = Customer(
            command.dni,
            command.first_names or "",
            command.last_names or "",
            user_id,
            command.phone,
            command.address,
        )
        await self._customers.add(customer)
        return customer, credentials
