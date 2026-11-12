from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class RegisterBcrpCapResource(BaseModel):
    # Bounded like the NUMERIC(12,7) column, so out-of-range values fail as validation errors.
    max_tea: Decimal = Field(gt=0, max_digits=12, decimal_places=7, examples=["114.68"])
    valid_from: date = Field(examples=["2027-05-01"])
    valid_to: date = Field(examples=["2027-10-31"])


class BcrpCapResource(BaseModel):
    id: int
    max_tea: Decimal
    max_late_tea: Decimal
    valid_from: date
    valid_to: date
