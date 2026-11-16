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
