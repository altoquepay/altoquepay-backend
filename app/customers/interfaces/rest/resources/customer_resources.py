from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.customers.domain.model.aggregates.store_customer import AccountStatus

# Bounded like the NUMERIC columns, so out-of-range values fail as validation errors.
RATE_FIELD = {"ge": 0, "max_digits": 12, "decimal_places": 7}
MONEY_FIELD = {"ge": 0, "max_digits": 12, "decimal_places": 2}


class OpenAccountResource(BaseModel):
    """Conditions left out take the store's defaults. Names are needed only for a new DNI."""

    dni: str = Field(max_length=8, examples=["45678912"])
    first_names: str | None = Field(None, max_length=100, examples=["Rosa"])
    last_names: str | None = Field(None, max_length=100, examples=["Quispe Mamani"])
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
    """id is the account (store_customers.id), the id every /customers/{id} route takes."""

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
    created_at: datetime


class CredentialsResource(BaseModel):
    """Shown once: the store hands the temporary password to the customer."""

    username: str
    temporary_password: str


class OpenedAccountResource(BaseModel):
    """credentials is null when the person already had a user from another store."""

    account: CustomerAccountResource
    credentials: CredentialsResource | None


class PersonLookupResource(BaseModel):
    """account_id is the person's account in this store, if any.

    notice is PERSON_HAS_ACCOUNT when the person already buys in another store: not an error,
    but they keep the user and password they already have.
    """

    customer_id: int
    dni: str
    first_names: str
    last_names: str
    phone: str | None
    address: str | None
    account_id: int | None
    notice: str | None
