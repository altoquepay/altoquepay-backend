"""Tests for the customer aggregate."""

import pytest

from app.customers.domain.model.aggregates.customer import Customer
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni


def test_names_are_trimmed_and_blank_contact_data_is_dropped():
    customer = Customer(Dni("01234567"), "  Rosa ", " Quispe ", 1, phone="  ", address=" Jr. Lima ")

    assert (customer.first_names, customer.last_names) == ("Rosa", "Quispe")
    assert (customer.phone, customer.address) == (None, "Jr. Lima")


@pytest.mark.parametrize(
    ("first_names", "last_names", "field"),
    [("  ", "Quispe", "first_names"), ("Rosa", "x" * 101, "last_names")],
)
def test_names_are_required_and_bounded(first_names, last_names, field):
    with pytest.raises(BusinessError) as error:
        Customer(Dni("01234567"), first_names, last_names, 1)

    assert (error.value.code, error.value.field) == ("INVALID_NAME", field)


def test_contact_update_keeps_the_dni_and_validates_again():
    customer = Customer(Dni("01234567"), "Rosa", "Quispe", 1, phone="987654321")

    customer.update_contact(" Rosa María ", "Quispe", "  ", "Jr. Lima")

    assert (customer.dni.value, customer.first_names) == ("01234567", "Rosa María")
    assert (customer.phone, customer.address) == (None, "Jr. Lima")
    with pytest.raises(BusinessError):
        customer.update_contact("", "Quispe", None, None)
