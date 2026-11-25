"""A purchase on credit, with its items and, when paid weekly, its installment schedule."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from app.credit.domain.services.credit_calculations import (
    capitalize,
    french_schedule,
    interest_over,
)
from app.shared.domain.errors import BusinessError
from app.shared.domain.finance import te7d
from app.shared.domain.value_objects import Money, Rate


class PaymentMode(StrEnum):
    SINGLE_DATE = "SINGLE_DATE"
    WEEKLY = "WEEKLY"


class PurchaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    PREPAID = "PREPAID"
    VOIDED = "VOIDED"


class InstallmentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    # Never stored: a pending installment past its due date is shown as overdue.
    OVERDUE = "OVERDUE"


@dataclass(frozen=True)
class PurchaseItem:
    """A product sold, at the list price it had when the purchase was registered."""

    product_id: int
    quantity: int
    unit_list_price: Money

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise BusinessError(
                "INVALID_QUANTITY", "Each item needs a quantity of at least 1.", field="quantity"
            )

    @property
    def subtotal(self) -> Money:
        return Money(self.unit_list_price.amount * self.quantity)


@dataclass
class Installment:
    number: int
    due_date: date
    opening_balance: Money
    interest: Money
    amortization: Money
    amount: Money
    closing_balance: Money
    status: InstallmentStatus = InstallmentStatus.PENDING
    payment_id: int | None = None
    id: int | None = None

    def status_on(self, today: date) -> InstallmentStatus:
        if self.status == InstallmentStatus.PENDING and self.due_date < today:
            return InstallmentStatus.OVERDUE
        return self.status


def already_paid() -> BusinessError:
    return BusinessError("ALREADY_PAID", "It was already paid.", status=409)


@dataclass
class Purchase:
    """The rates are copied from the account when registered, so later changes do not affect it.

    A single date purchase has term_days; a weekly one has the grace, the capitalized amount,
    the weekly rate and its installments. ordinary_interest is what the customer pays on top of
    the amount: the term interest, or the sum of the schedule interests.
    """

    store_id: int
    account_id: int
    cycle_id: int
    purchased_at: datetime
    mode: PaymentMode
    items: list[PurchaseItem]
    tea: Rate
    late_tea: Rate
    ordinary_interest: Money
    created_by: int
    term_days: int | None = None
    grace_days: int | None = None
    capitalized_amount: Money | None = None
    weekly_rate: Rate | None = None
    installments_count: int | None = None
    installment_amount: Money | None = None
    installments: list[Installment] = field(default_factory=list)
    status: PurchaseStatus = PurchaseStatus.ACTIVE
    payment_id: int | None = None
    voided_at: datetime | None = None
    voided_by: int | None = None
    id: int | None = None

    @property
    def amount(self) -> Money:
        return Money(sum((item.subtotal.amount for item in self.items), Decimal(0)))

    @property
    def total(self) -> Money:
        """Return what the customer pays without late interest: amount plus ordinary interest.

        A weekly purchase also pays the grace interest, so its total is its installments.
        """
        if self.mode == PaymentMode.WEEKLY:
            return Money(sum((i.amount.amount for i in self.installments), Decimal(0)))
        return Money(self.amount.amount + self.ordinary_interest.amount)

    @classmethod
    def register(
        cls,
        *,
        store_id: int,
        account_id: int,
        cycle_id: int,
        cycle_payment_date: date,
        purchased_at: datetime,
        purchase_day: date,
        mode: PaymentMode,
        items: list[PurchaseItem],
        tea: Rate,
        late_tea: Rate,
        installments_count: int | None,
        max_weeks: int,
        created_by: int,
    ) -> "Purchase":
        """Calculate the purchase. purchase_day is the day of purchased_at in the business zone."""
        if not items:
            raise BusinessError("NO_ITEMS", "A purchase needs at least one item.", field="items")
        if len({item.product_id for item in items}) < len(items):
            raise BusinessError(
                "DUPLICATE_PRODUCT", "Each product goes in one item only.", field="items"
            )
        days = (cycle_payment_date - purchase_day).days
        purchase = cls(
            store_id=store_id,
            account_id=account_id,
            cycle_id=cycle_id,
            purchased_at=purchased_at,
            mode=mode,
            items=items,
            tea=tea,
            late_tea=late_tea,
            ordinary_interest=Money(Decimal(0)),
            created_by=created_by,
        )
        if mode == PaymentMode.SINGLE_DATE:
            if installments_count is not None:
                raise BusinessError(
                    "INVALID_INSTALLMENTS_COUNT",
                    "A single date purchase has no installments.",
                    field="installments_count",
                )
            purchase.term_days = days
            purchase.ordinary_interest = interest_over(purchase.amount, tea, days)
            return purchase
        if installments_count is None or installments_count < 1:
            raise BusinessError(
                "INVALID_INSTALLMENTS_COUNT",
                "A weekly purchase needs at least one installment.",
                field="installments_count",
            )
        if installments_count > max_weeks:
            raise BusinessError(
                "MAX_WEEKS_EXCEEDED",
                f"The installments exceed the maximum weeks of this customer ({max_weeks}).",
                field="installments_count",
                details={"max": str(max_weeks)},
            )
        purchase.grace_days = days
        purchase.capitalized_amount = capitalize(purchase.amount, tea, days)
        purchase.weekly_rate = Rate(te7d(tea))
        purchase.installments_count = installments_count
        schedule = french_schedule(
            purchase.capitalized_amount, tea, installments_count, cycle_payment_date
        )
        purchase.installments = [
            Installment(
                row.number,
                row.due_date,
                row.opening_balance,
                row.interest,
                row.amortization,
                row.amount,
                row.closing_balance,
            )
            for row in schedule
        ]
        purchase.installment_amount = schedule[0].amount
        purchase.ordinary_interest = Money(
            sum((row.interest.amount for row in schedule), Decimal(0))
        )
        return purchase

    def outstanding_principal(self) -> Money:
        """Return the principal owed: the amount, or the amortization of pending installments."""
        if self.status != PurchaseStatus.ACTIVE:
            return Money(Decimal(0))
        if self.mode == PaymentMode.SINGLE_DATE:
            return self.amount
        pending = (i for i in self.installments if i.status == InstallmentStatus.PENDING)
        return Money(sum((i.amortization.amount for i in pending), Decimal(0)))

    def find_installment(self, installment_id: int) -> Installment:
        for installment in self.installments:
            if installment.id == installment_id:
                return installment
        raise BusinessError("NOT_FOUND", "The installment does not exist.", status=404)

    def mark_installment_paid(self, installment_id: int, payment_id: int) -> None:
        """Pay an installment. Paying the last pending one pays the purchase."""
        installment = self.find_installment(installment_id)
        if installment.status != InstallmentStatus.PENDING:
            raise already_paid()
        installment.status = InstallmentStatus.PAID
        installment.payment_id = payment_id
        if all(i.status != InstallmentStatus.PENDING for i in self.installments):
            self.status = PurchaseStatus.PAID

    def mark_paid(self, payment_id: int) -> None:
        """Pay a single date purchase, on its date or early."""
        if self.mode != PaymentMode.SINGLE_DATE:
            raise BusinessError(
                "NOT_SINGLE_DATE", "Only a single date purchase is paid at once.", status=409
            )
        if self.status != PurchaseStatus.ACTIVE:
            raise already_paid()
        self.status = PurchaseStatus.PAID
        self.payment_id = payment_id

    def cancel_remaining_installments(self, payment_id: int) -> None:
        """Prepay a weekly purchase: the pending installments are cancelled by that payment."""
        if self.mode != PaymentMode.WEEKLY:
            raise BusinessError(
                "NOT_WEEKLY", "Only a weekly purchase has installments to cancel.", status=409
            )
        if self.status != PurchaseStatus.ACTIVE:
            raise already_paid()
        for installment in self.installments:
            if installment.status == InstallmentStatus.PENDING:
                installment.status = InstallmentStatus.CANCELLED
                installment.payment_id = payment_id
        self.status = PurchaseStatus.PREPAID
        self.payment_id = payment_id

    def void(self, user_id: int, now: datetime) -> None:
        """Void a purchase registered by mistake, while nothing of it is paid.

        Its installments are cancelled, so it stops counting against the credit limit and is
        left out of the statement. Credit checks first that its cycle is still open.
        """
        if self.status != PurchaseStatus.ACTIVE or any(
            i.status != InstallmentStatus.PENDING for i in self.installments
        ):
            raise BusinessError(
                "PURCHASE_NOT_VOIDABLE",
                "Only a purchase with nothing paid can be voided.",
                status=409,
            )
        for installment in self.installments:
            installment.status = InstallmentStatus.CANCELLED
        self.status = PurchaseStatus.VOIDED
        self.voided_at = now
        self.voided_by = user_id


def outstanding_principal_of(purchases: list[Purchase]) -> Money:
    """Return the principal owed on the purchases, what counts against the credit limit."""
    return Money(sum((p.outstanding_principal().amount for p in purchases), Decimal(0)))
