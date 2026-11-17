from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.model.aggregates.store_customer import (
    CURRENCY,
    AccountStatus,
    StoreCustomer,
)
from app.customers.infrastructure.persistence.models import CustomerModel, StoreCustomerModel
from app.shared.domain.value_objects import CreditConditions, Dni, Money, Rate


def customer_to_domain(model: CustomerModel) -> Customer:
    return Customer(
        dni=Dni(model.dni),
        first_names=model.first_names,
        last_names=model.last_names,
        user_id=model.user_id,
        phone=model.phone,
        address=model.address,
        id=model.id,
    )


def copy_customer_to_model(customer: Customer, model: CustomerModel) -> CustomerModel:
    model.dni = customer.dni.value
    model.first_names = customer.first_names
    model.last_names = customer.last_names
    model.phone = customer.phone
    model.address = customer.address
    model.user_id = customer.user_id
    return model


def account_to_domain(model: StoreCustomerModel) -> StoreCustomer:
    return StoreCustomer(
        store_id=model.store_id,
        customer_id=model.customer_id,
        credit_limit=Money(model.credit_limit),
        conditions=CreditConditions(
            cutoff_day=model.cutoff_day,
            payment_day=model.payment_day,
            tea=Rate.from_percent(model.tea),
            late_tea=Rate.from_percent(model.late_tea),
            max_weeks=model.max_weeks,
        ),
        status=AccountStatus(model.status),
        created_at=model.created_at,
        portal_linked_at=model.portal_linked_at,
        access_code_hash=model.access_code_hash,
        access_code_expires_at=model.access_code_expires_at,
        id=model.id,
    )


def copy_account_to_model(account: StoreCustomer, model: StoreCustomerModel) -> StoreCustomerModel:
    conditions = account.conditions
    model.store_id = account.store_id
    model.customer_id = account.customer_id
    model.currency = CURRENCY
    model.credit_limit = account.credit_limit.amount
    model.tea = conditions.tea.percent
    model.late_tea = conditions.late_tea.percent
    model.cutoff_day = conditions.cutoff_day
    model.payment_day = conditions.payment_day
    model.max_weeks = conditions.max_weeks
    model.status = account.status.value
    model.portal_linked_at = account.portal_linked_at
    model.access_code_hash = account.access_code_hash
    model.access_code_expires_at = account.access_code_expires_at
    return model
