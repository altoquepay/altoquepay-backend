from decimal import Decimal

from pydantic import BaseModel, Field

# Bounded like the NUMERIC(12,2) columns, so out-of-range prices fail as validation errors.
MONEY_FIELD = {"ge": 0, "max_digits": 12, "decimal_places": 2}


class ProductDetailsResource(BaseModel):
    code: str = Field(max_length=30, examples=["ARR-5"])
    description: str = Field(max_length=200, examples=["Arroz extra 5 kg"])
    brand: str = Field(max_length=100, examples=["Costeño"])
    category: str = Field(max_length=100, examples=["Abarrotes"])
    unit: str = Field(max_length=20, examples=["bolsa"])
    supplier: str | None = Field(None, max_length=100, examples=["Distribuidora Lima"])
    cash_price: Decimal = Field(**MONEY_FIELD, examples=["21.50"])
    # The price on credit, which purchases charge.
    list_price: Decimal = Field(**MONEY_FIELD, examples=["23.90"])


class ProductResource(BaseModel):
    id: int
    code: str
    description: str
    brand: str
    category: str
    unit: str
    supplier: str | None
    cash_price: Decimal
    list_price: Decimal
    # A path on this API, such as /media/products/3/12-a1b2.png, or null.
    image_url: str | None
    is_active: bool
