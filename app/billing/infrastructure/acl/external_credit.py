from datetime import date

from app.billing.application.ports.credit_ledger import CreditLedger, InstallmentInfo, PurchaseInfo
from app.credit.interfaces.acl.credit_facade import (
    CreditFacade,
    InstallmentSummary,
    PurchaseSummary,
)
from app.shared.domain.value_objects import Money, Rate

# Wide enough to cover every installment an account can have.
FIRST_DAY = date(1, 1, 1)
LAST_DAY = date(9999, 12, 31)


def to_purchase_info(purchase: PurchaseSummary) -> PurchaseInfo:
    return PurchaseInfo(
        purchase_id=purchase.purchase_id,
        account_id=purchase.account_id,
        cycle_id=purchase.cycle_id,
        purchased_at=purchase.purchased_at,
        mode=purchase.mode,
        amount=Money(purchase.amount),
        tea=Rate.from_percent(purchase.tea),
        late_tea=Rate.from_percent(purchase.late_tea),
        ordinary_interest=Money(purchase.ordinary_interest),
        status=purchase.status,
    )


def to_installment_info(installment: InstallmentSummary) -> InstallmentInfo:
    return InstallmentInfo(
        installment_id=installment.installment_id,
        purchase_id=installment.purchase_id,
        account_id=installment.account_id,
        number=installment.number,
        due_date=installment.due_date,
        opening_balance=Money(installment.opening_balance),
        interest=Money(installment.interest),
        amortization=Money(installment.amortization),
        amount=Money(installment.amount),
        status=installment.status,
    )


class ExternalCredit(CreditLedger):
    def __init__(self, credit_facade: CreditFacade) -> None:
        self._credit_facade = credit_facade

    async def get_purchase(self, purchase_id: int) -> PurchaseInfo:
        return to_purchase_info(await self._credit_facade.get_purchase(purchase_id))

    async def get_installment(self, installment_id: int) -> InstallmentInfo:
        return to_installment_info(await self._credit_facade.get_installment(installment_id))

    async def pending_installments(self, account_id: int) -> list[InstallmentInfo]:
        due = await self._credit_facade.get_installments_due(account_id, FIRST_DAY, LAST_DAY)
        return [to_installment_info(installment) for installment in due]

    async def cycle_purchases(self, cycle_id: int) -> list[PurchaseInfo]:
        purchases = await self._credit_facade.get_cycle_purchases(cycle_id)
        return [to_purchase_info(purchase) for purchase in purchases]

    async def mark_installment_paid(self, installment_id: int, payment_id: int) -> None:
        await self._credit_facade.mark_installment_paid(installment_id, payment_id)

    async def mark_purchase_paid(self, purchase_id: int, payment_id: int) -> None:
        await self._credit_facade.mark_purchase_paid(purchase_id, payment_id)

    async def cancel_remaining_installments(self, purchase_id: int, payment_id: int) -> None:
        await self._credit_facade.cancel_remaining_installments(purchase_id, payment_id)
