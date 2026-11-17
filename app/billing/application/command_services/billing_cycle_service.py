from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.billing.application.ports.account_directory import AccountDirectory
from app.billing.domain.model.aggregates.billing_cycle import BillingCycle
from app.billing.domain.repositories.billing_cycle_repository import BillingCycleRepository
from app.billing.domain.services.cycle_assignment import CyclePeriod, cycle_period_of
from app.shared.domain.errors import BusinessError


class BillingCycleService:
    """Never commits: the purchase and its cycle are confirmed together by credit."""

    def __init__(
        self,
        cycles: BillingCycleRepository,
        accounts: AccountDirectory,
        business_time_zone: ZoneInfo,
    ) -> None:
        self._cycles = cycles
        self._accounts = accounts
        self._business_time_zone = business_time_zone

    async def get_or_open(
        self, account_id: int, purchased_at: datetime, today: date
    ) -> BillingCycle:
        """Return the open cycle of a purchase, creating it if the account has none yet.

        A cycle whose cutoff day ended before today is closed even if no read closed it yet,
        so a purchase dated in it is refused. Credit locks the account first, so two purchases
        cannot create the same cycle twice. The cycle is locked too, so a read closing it at
        midnight either waits for the purchase or makes it see the cycle closed.
        """
        if purchased_at.tzinfo is None:
            raise ValueError("purchased_at must have a time zone.")
        # The cutoff ends at midnight in the store's time zone, not the server's.
        purchase_day = purchased_at.astimezone(self._business_time_zone).date()
        account = await self._accounts.get_account(account_id)
        period = cycle_period_of(purchase_day, account.cutoff_day, account.payment_day)
        if period.cutoff_date < today:
            raise cycle_closed(period)
        cycle = await self._cycles.find(account_id, period.year, period.month, for_update=True)
        if cycle is None:
            cycle = BillingCycle.open(account_id, account.store_id, period)
            await self._cycles.add(cycle)
        elif not cycle.is_open:
            raise cycle_closed(period)
        return cycle


def cycle_closed(period: CyclePeriod) -> BusinessError:
    return BusinessError(
        "CYCLE_CLOSED",
        f"The cycle of {period.month:02d}/{period.year} is already closed.",
        status=409,
    )
