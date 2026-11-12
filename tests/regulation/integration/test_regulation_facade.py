"""Tests for the regulation facade against the seeded BCRP caps."""

from datetime import date
from decimal import Decimal

import pytest

from app.regulation.interfaces.acl.regulation_facade import RegulationFacade
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork

NOVEMBER_2026 = date(2026, 11, 12)


@pytest.fixture
async def facade():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield RegulationFacade(unit_of_work)


async def test_rates_equal_to_the_caps_are_allowed(facade):
    await facade.validate_rates(Decimal("114.68"), Decimal("17.202"), NOVEMBER_2026)


@pytest.mark.parametrize(
    ("tea", "late_tea", "field", "maximum"),
    [
        (Decimal("114.69"), Decimal("10"), "tea", "114.68"),
        (Decimal("75"), Decimal("17.21"), "late_tea", "17.202"),
    ],
)
async def test_rate_above_its_cap_is_rejected_on_its_field(facade, tea, late_tea, field, maximum):
    with pytest.raises(BusinessError) as error:
        await facade.validate_rates(tea, late_tea, NOVEMBER_2026)

    assert error.value.code == "RATE_ABOVE_BCRP_CAP"
    assert error.value.field == field
    assert error.value.details == {"max": maximum}
    assert f"(max {maximum}%)" in error.value.message


async def test_dates_before_november_use_the_previous_cap(facade):
    with pytest.raises(BusinessError) as error:
        await facade.validate_rates(Decimal("114.5"), Decimal("10"), date(2026, 10, 15))
    assert error.value.details == {"max": "114.13"}


async def test_current_cap_includes_its_period_and_late_cap(facade):
    cap = await facade.get_current_cap(NOVEMBER_2026)

    assert (cap.max_tea, cap.max_late_tea) == (Decimal("114.6800000"), Decimal("17.2020000"))
    assert (cap.valid_from, cap.valid_to) == (date(2026, 11, 1), date(2027, 4, 30))


async def test_date_without_cap_is_reported(facade):
    with pytest.raises(BusinessError) as error:
        await facade.validate_rates(Decimal("75"), Decimal("10"), date(2027, 5, 1))
    assert (error.value.code, error.value.status) == ("NO_BCRP_CAP_IN_FORCE", 409)
