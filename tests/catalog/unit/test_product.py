"""Tests for the product aggregate."""

from decimal import Decimal

import pytest

from app.catalog.domain.model.aggregates.product import Product, ProductDetails
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money


def product(**changes) -> Product:
    values = {
        "store_id": 1,
        "code": " ARR-5 ",
        "description": "Arroz extra 5 kg",
        "brand": "Costeño",
        "category": "Abarrotes",
        "unit": "bolsa",
        "cash_price": Money(Decimal("21.50")),
        "list_price": Money(Decimal("23.90")),
    }
    return Product(**(values | changes))


def test_texts_are_trimmed_and_blank_optional_ones_are_dropped():
    created = product(supplier="  ", image_url=" https://img.pe/arroz.png ")

    assert created.code == "ARR-5"
    assert (created.supplier, created.image_url) == (None, "https://img.pe/arroz.png")
    assert created.is_active


@pytest.mark.parametrize(
    ("changes", "field"),
    [({"code": "  "}, "code"), ({"unit": "x" * 21}, "unit"), ({"supplier": "x" * 101}, "supplier")],
)
def test_texts_outside_their_length_are_rejected(changes, field):
    with pytest.raises(BusinessError) as error:
        product(**changes)

    assert (error.value.code, error.value.field) == ("INVALID_TEXT", field)


def test_deactivated_product_is_kept_but_inactive():
    created = product()

    created.deactivate()

    assert not created.is_active


def test_update_replaces_the_details_and_validates_again():
    created = product()
    details = ProductDetails(
        code="ARR-1",
        description="Arroz extra 1 kg",
        brand="Costeño",
        category="Abarrotes",
        unit="bolsa",
        cash_price=Money(Decimal("4.50")),
        list_price=Money(Decimal("4.90")),
        supplier=" Distribuidora Lima ",
    )

    created.update(details)

    assert (created.code, created.list_price, created.supplier) == (
        "ARR-1",
        Money(Decimal("4.90")),
        "Distribuidora Lima",
    )
    with pytest.raises(BusinessError):
        created.update(ProductDetails("", "x", "x", "x", "x", Money(Decimal(1)), Money(Decimal(1))))
