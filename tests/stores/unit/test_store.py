"""Tests for the Store aggregate."""

from decimal import Decimal

import pytest

from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import CreditConditions, Rate, Ruc
from app.stores.domain.model.aggregates.store import Store, StoreStatus

RUC = Ruc("20123456789")


def test_a_new_store_is_active_with_the_initial_conditions():
    store = Store.register("  Bodega La Esquina ", RUC)

    assert (store.business_name, store.status) == ("Bodega La Esquina", StoreStatus.ACTIVE)
    conditions = store.default_conditions
    assert (conditions.cutoff_day, conditions.payment_day, conditions.max_weeks) == (10, 15, 4)
    assert (conditions.tea.percent, conditions.late_tea.percent) == (Decimal("40"), Decimal("15"))


@pytest.mark.parametrize("invalid_name", ["", "   ", "x" * 151])
def test_business_name_is_required_and_bounded(invalid_name):
    with pytest.raises(BusinessError) as error:
        Store.register(invalid_name, RUC)
    assert (error.value.code, error.value.field) == ("INVALID_BUSINESS_NAME", "business_name")


def test_profile_update_keeps_the_ruc_and_clears_blank_contact_data():
    store = Store.register("Bodega La Esquina", RUC)
    conditions = CreditConditions(20, 26, Rate.from_percent(Decimal("50")), Rate(Decimal("0")), 8)

    store.update_profile("Bodega Don Lucho", "  ", " 987654321 ", conditions)

    assert (store.business_name, store.ruc, store.address, store.phone) == (
        "Bodega Don Lucho",
        RUC,
        None,
        "987654321",
    )
    assert store.default_conditions == conditions


def test_store_can_be_deactivated_and_reactivated():
    store = Store.register("Bodega La Esquina", RUC)

    store.deactivate()
    assert not store.is_active

    store.reactivate()
    assert store.is_active
