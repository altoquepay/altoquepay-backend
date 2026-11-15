from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.stores.domain.model.aggregates.store import StoreStatus


class RegisterStoreResource(BaseModel):
    business_name: str = Field(max_length=150, examples=["Bodega La Esquina"])
    ruc: str = Field(max_length=11, examples=["10456781234"])
    # The frontend joins the names and surnames of the form.
    full_name: str = Field(max_length=150, examples=["Rosa Quispe Mamani"])
    email: str = Field(max_length=254, examples=["rosa@bodegalaesquina.pe"])
    password: str = Field(max_length=128, examples=["mi-clave-segura"])


# Bounded like the NUMERIC(12,7) columns, so out-of-range rates fail as validation errors.
RATE_FIELD = {"ge": 0, "max_digits": 12, "decimal_places": 7}


class UpdateStoreProfileResource(BaseModel):
    business_name: str = Field(max_length=150, examples=["Bodega La Esquina"])
    address: str | None = Field(None, max_length=200, examples=["Av. Los Jardines 123, SJL"])
    phone: str | None = Field(None, max_length=20, examples=["987654321"])
    default_cutoff_day: int = Field(examples=[10])
    default_payment_day: int = Field(examples=[15])
    default_tea: Decimal = Field(**RATE_FIELD, examples=["40"])
    default_late_tea: Decimal = Field(**RATE_FIELD, examples=["15"])
    default_max_weeks: int = Field(examples=[4])


class StoreResource(BaseModel):
    id: int
    business_name: str
    ruc: str
    address: str | None
    phone: str | None
    status: StoreStatus
    registered_at: datetime
    default_cutoff_day: int
    default_payment_day: int
    default_tea: Decimal
    default_late_tea: Decimal
    default_max_weeks: int


class StoreListItemResource(BaseModel):
    id: int
    business_name: str
    ruc: str
    status: StoreStatus
    registered_at: datetime
    customers_count: int
