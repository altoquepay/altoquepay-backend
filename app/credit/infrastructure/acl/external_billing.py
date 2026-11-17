from datetime import date, datetime

from app.billing.interfaces.acl.billing_facade import BillingFacade
from app.credit.application.ports.cycle_assigner import AssignedCycle, CycleAssigner


class ExternalBilling(CycleAssigner):
    def __init__(self, billing_facade: BillingFacade) -> None:
        self._billing_facade = billing_facade

    async def cycle_of(self, account_id: int, purchased_at: datetime, today: date) -> AssignedCycle:
        cycle = await self._billing_facade.get_or_open_cycle(account_id, purchased_at, today)
        return AssignedCycle(cycle.cycle_id, cycle.payment_date)
