from app.customers.application.command_services.account_command_service import OpenedAccount
from app.customers.application.ports.customer_users import CustomerCredentials
from app.customers.application.query_services.account_query_service import (
    CustomerAccount,
    PersonLookup,
)
from app.customers.domain.model.commands.open_account_command import OpenAccountCommand
from app.customers.domain.model.commands.update_account_command import UpdateAccountCommand
from app.customers.interfaces.rest.resources.customer_resources import (
    CredentialsResource,
    CustomerAccountResource,
    OpenAccountResource,
    OpenedAccountResource,
    PersonLookupResource,
    UpdateAccountResource,
)
from app.shared.domain.value_objects import CreditConditions, Dni, Money, Rate


def to_open_command(resource: OpenAccountResource, store_id: int) -> OpenAccountCommand:
    return OpenAccountCommand(
        store_id=store_id,
        dni=Dni(resource.dni.strip()),
        first_names=resource.first_names,
        last_names=resource.last_names,
        phone=resource.phone,
        address=resource.address,
        credit_limit=Money(resource.credit_limit),
        cutoff_day=resource.cutoff_day,
        payment_day=resource.payment_day,
        tea=resource.tea,
        late_tea=resource.late_tea,
        max_weeks=resource.max_weeks,
    )


def to_update_command(
    resource: UpdateAccountResource, store_id: int, account_id: int
) -> UpdateAccountCommand:
    return UpdateAccountCommand(
        store_id=store_id,
        account_id=account_id,
        first_names=resource.first_names,
        last_names=resource.last_names,
        phone=resource.phone,
        address=resource.address,
        credit_limit=Money(resource.credit_limit),
        conditions=CreditConditions(
            cutoff_day=resource.cutoff_day,
            payment_day=resource.payment_day,
            tea=Rate.from_percent(resource.tea),
            late_tea=Rate.from_percent(resource.late_tea),
            max_weeks=resource.max_weeks,
        ),
    )


def to_resource(found: CustomerAccount) -> CustomerAccountResource:
    account, customer = found.account, found.customer
    if account.id is None or account.created_at is None or customer.id is None:
        raise ValueError("Only a stored account has a resource.")
    conditions = account.conditions
    return CustomerAccountResource(
        id=account.id,
        customer_id=customer.id,
        dni=customer.dni.value,
        first_names=customer.first_names,
        last_names=customer.last_names,
        phone=customer.phone,
        address=customer.address,
        credit_limit=account.credit_limit.amount,
        cutoff_day=conditions.cutoff_day,
        payment_day=conditions.payment_day,
        tea=conditions.tea.percent,
        late_tea=conditions.late_tea.percent,
        max_weeks=conditions.max_weeks,
        status=account.status,
        created_at=account.created_at,
    )


def to_credentials_resource(credentials: CustomerCredentials) -> CredentialsResource:
    return CredentialsResource(
        username=credentials.username, temporary_password=credentials.temporary_password
    )


def to_opened_resource(opened: OpenedAccount) -> OpenedAccountResource:
    credentials = opened.credentials
    return OpenedAccountResource(
        account=to_resource(opened.customer_account),
        credentials=to_credentials_resource(credentials) if credentials else None,
    )


def to_lookup_resource(lookup: PersonLookup) -> PersonLookupResource:
    customer = lookup.customer
    if customer.id is None:
        raise ValueError("Only a stored customer has a resource.")
    return PersonLookupResource(
        customer_id=customer.id,
        dni=customer.dni.value,
        first_names=customer.first_names,
        last_names=customer.last_names,
        phone=customer.phone,
        address=customer.address,
        account_id=lookup.account_id,
        notice=lookup.notice,
    )
