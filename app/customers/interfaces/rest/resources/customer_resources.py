from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.customers.domain.model.aggregates.store_customer import AccountStatus

# Bounded like the NUMERIC columns, so out-of-range values fail as validation errors.
RATE_FIELD = {"ge": 0, "max_digits": 12, "decimal_places": 7}
MONEY_FIELD = {"ge": 0, "max_digits": 12, "decimal_places": 2}


class OpenAccountResource(BaseModel):
    """Conditions left out take the store's defaults.

    The names are how this store knows the person, so they are needed even for a DNI that
    already buys in another store.
    """

    dni: str = Field(max_length=8, examples=["45678912"])
    first_names: str = Field(max_length=100, examples=["Rosa"])
    last_names: str = Field(max_length=100, examples=["Quispe Mamani"])
    phone: str | None = Field(None, max_length=20, examples=["987654321"])
    address: str | None = Field(None, max_length=200, examples=["Jr. Los Pinos 456, SJL"])
    credit_limit: Decimal = Field(**MONEY_FIELD, examples=["1500"])
    cutoff_day: int | None = Field(None, examples=[20])
    payment_day: int | None = Field(None, examples=[26])
    tea: Decimal | None = Field(None, **RATE_FIELD, examples=["75"])
    late_tea: Decimal | None = Field(None, **RATE_FIELD, examples=["10"])
    max_weeks: int | None = Field(None, examples=[4])


class UpdateAccountResource(BaseModel):
    first_names: str = Field(max_length=100, examples=["Rosa"])
    last_names: str = Field(max_length=100, examples=["Quispe Mamani"])
    phone: str | None = Field(None, max_length=20, examples=["987654321"])
    address: str | None = Field(None, max_length=200, examples=["Jr. Los Pinos 456, SJL"])
    credit_limit: Decimal = Field(**MONEY_FIELD, examples=["2000"])
    cutoff_day: int = Field(examples=[20])
    payment_day: int = Field(examples=[26])
    tea: Decimal = Field(**RATE_FIELD, examples=["75"])
    late_tea: Decimal = Field(**RATE_FIELD, examples=["10"])
    max_weeks: int = Field(examples=[4])


class CustomerAccountResource(BaseModel):
    """id is the account (store_customers.id), the id every /customers/{id} route takes.

    portal_linked is false until the customer redeems an access code of this store, so the
    store knows it still has to hand one over.
    """

    id: int
    customer_id: int
    dni: str
    first_names: str
    last_names: str
    phone: str | None
    address: str | None
    credit_limit: Decimal
    cutoff_day: int
    payment_day: int
    tea: Decimal
    late_tea: Decimal
    max_weeks: int
    status: AccountStatus
    portal_linked: bool
    created_at: datetime


class AccessCodeResource(BaseModel):
    """Shown once: the store hands the code to the customer, who redeems it before expires_at."""

    code: str
    expires_at: datetime


class OpenedAccountResource(BaseModel):
    """The access code links this account to the customer's portal, new person or not."""

    account: CustomerAccountResource
    access_code: AccessCodeResource


class LinkStoreResource(BaseModel):
    code: str = Field(max_length=20, examples=["K7QH-M2XW-PB9D"])


class TrustStoreResource(BaseModel):
    """The DNI goes in the body, so it stays out of the access logs."""

    dni: str = Field(max_length=8, examples=["45678912"])
    store_id: int


class PersonLookupResource(BaseModel):
    """account_id is the person's account in this store, if any.

    notice is PERSON_HAS_ACCOUNT when the person already buys in another store: not an error,
    but they keep the user and password they already have, and add this store with its code.
    What other stores typed about the person is never shown; read the own account instead.
    """

    customer_id: int
    dni: str
    account_id: int | None
    notice: str | None
