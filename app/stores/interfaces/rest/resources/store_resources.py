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
