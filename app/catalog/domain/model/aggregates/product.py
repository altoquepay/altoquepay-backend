"""Something a store sells on credit. The catalog keeps no stock."""

from dataclasses import dataclass

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money

# Maximum lengths of the required and optional texts, as in the products table.
REQUIRED_TEXT_LENGTHS = {
    "code": 30,
    "description": 200,
    "brand": 100,
    "category": 100,
    "unit": 20,
}
OPTIONAL_TEXT_LENGTHS = {"supplier": 100, "image_url": 500}


@dataclass
class Product:
    """A deactivated product keeps its past sales, but cannot be sold anymore."""

    store_id: int
    code: str
    description: str
    brand: str
    category: str
    unit: str
    cash_price: Money
    list_price: Money
    supplier: str | None = None
    image_url: str | None = None
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        for field, maximum in REQUIRED_TEXT_LENGTHS.items():
            text = getattr(self, field).strip()
            if not 1 <= len(text) <= maximum:
                raise invalid_text(field, 1, maximum)
            setattr(self, field, text)
        for field, maximum in OPTIONAL_TEXT_LENGTHS.items():
            text = (getattr(self, field) or "").strip() or None
            if text is not None and len(text) > maximum:
                raise invalid_text(field, 0, maximum)
            setattr(self, field, text)

    def deactivate(self) -> None:
        self.is_active = False


def invalid_text(field: str, minimum: int, maximum: int) -> BusinessError:
    return BusinessError(
        "INVALID_TEXT",
        f"The {field.replace('_', ' ')} must have between {minimum} and {maximum} characters.",
        field=field,
    )
