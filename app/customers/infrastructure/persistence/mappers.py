from app.customers.domain.model.aggregates.customer import Customer
from app.customers.domain.model.aggregates.store_customer import (
    CURRENCY,
    AccountStatus,
    StoreCustomer,
)
from app.customers.infrastructure.persistence.models import CustomerModel, StoreCustomerModel
from app.shared.domain.value_objects import CreditConditions, Money, Rate


def customer_to_model(customer: Customer) -> CustomerModel:
    return CustomerModel(
        dni=customer.dni.value,
        first_names=customer.first_names,
        last_names=customer.last_names,
        phone=customer.phone,
        address=customer.address,
        user_id=customer.user_id,
    )


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
        id=model.id,
    )


def account_to_model(account: StoreCustomer) -> StoreCustomerModel:
    conditions = account.conditions
    return StoreCustomerModel(
        store_id=account.store_id,
        customer_id=account.customer_id,
        currency=CURRENCY,
        credit_limit=account.credit_limit.amount,
        tea=conditions.tea.percent,
        late_tea=conditions.late_tea.percent,
        cutoff_day=conditions.cutoff_day,
        payment_day=conditions.payment_day,
        max_weeks=conditions.max_weeks,
        status=account.status.value,
    )
