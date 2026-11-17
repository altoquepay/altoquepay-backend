"""A customer account saved in the session of a test, for the tables that reference it."""

from datetime import UTC, datetime
from decimal import Decimal

from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.model.aggregates.store_customer import AccountStatus, StoreCustomer
from app.customers.infrastructure.persistence.customer_repository_impl import (
    CustomerRepositoryImpl,
)
from app.customers.infrastructure.persistence.store_customer_repository_impl import (
    StoreCustomerRepositoryImpl,
)
from app.iam.domain.model.aggregates.user import User
from app.iam.infrastructure.persistence.user_repository_impl import UserRepositoryImpl
from app.shared.domain.value_objects import CreditConditions, Dni, Money, Rate
from app.shared.infrastructure.unit_of_work import UnitOfWork


async def add_customer(unit_of_work: UnitOfWork, dni: str = "70000001") -> Customer:
    """Flush a new customer with its user, without committing them."""
    user = User.customer(Dni(dni), "unused-hash")
    await UserRepositoryImpl(unit_of_work.session).add(user)
    assert user.id is not None
    customer = Customer(Dni(dni), "Rosa", "Quispe Mamani", user.id)
    await CustomerRepositoryImpl(unit_of_work.session).add(customer)
    return customer


async def add_account(
    unit_of_work: UnitOfWork,
    store_id: int,
    customer_id: int,
    cutoff_day: int = 20,
    payment_day: int = 26,
    status: AccountStatus = AccountStatus.ACTIVE,
    portal_linked: bool = True,
) -> StoreCustomer:
    """Flush a new account with a 75% TEA and a 10% late TEA, without committing it.

    It is in the customer's portal unless portal_linked is False.
    """
    account = StoreCustomer(
        store_id=store_id,
        customer_id=customer_id,
        credit_limit=Money(Decimal("1500")),
        conditions=CreditConditions(
            cutoff_day=cutoff_day,
            payment_day=payment_day,
            tea=Rate.from_percent(Decimal("75")),
            late_tea=Rate.from_percent(Decimal("10")),
            max_weeks=4,
        ),
        status=status,
        portal_linked_at=datetime.now(UTC) if portal_linked else None,
    )
    await StoreCustomerRepositoryImpl(unit_of_work.session).add(account)
    return account
