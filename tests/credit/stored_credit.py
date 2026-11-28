"""The store, account, product and cycle a purchase needs, saved in the session of a test."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.billing.domain.model.aggregates.payment import Payment, PaymentBreakdown, PaymentKind
from app.billing.infrastructure.persistence.payment_repository_impl import PaymentRepositoryImpl
from app.billing.interfaces.acl.billing_facade import BillingFacade
from app.catalog.domain.model.aggregates.product import Product
from app.catalog.infrastructure.persistence.product_repository_impl import ProductRepositoryImpl
from app.credit.domain.model.aggregates.purchase import PaymentMode, Purchase, PurchaseItem
from app.credit.infrastructure.persistence.purchase_repository_impl import PurchaseRepositoryImpl
from app.shared.domain.value_objects import Money, Rate
from app.shared.infrastructure.unit_of_work import UnitOfWork
from tests.stored_account import add_account, add_customer
from tests.stored_store import add_store

LIMA = ZoneInfo("America/Lima")


@dataclass(frozen=True)
class CreditSetup:
    store_id: int
    account_id: int
    product_id: int
    user_id: int


async def add_product(
    unit_of_work: UnitOfWork, store_id: int, code: str = "GAS-15", price: str = "100.00"
) -> Product:
    product = Product(
        store_id=store_id,
        code=code,
        description=f"Producto {code}",
        brand="Marca",
        category="Abarrotes",
        unit="unidad",
        cash_price=Money(Decimal(price)),
        list_price=Money(Decimal(price)),
    )
    await ProductRepositoryImpl(unit_of_work.session).add(product)
    return product


async def add_credit_setup(
    unit_of_work: UnitOfWork, ruc: str = "20999999990", dni: str = "70000001", cutoff_day=14
) -> CreditSetup:
    """A store with one product at S/ 100 and one account: TEA 75%, cutoff 14, payment 26."""
    store = await add_store(unit_of_work, ruc)
    customer = await add_customer(unit_of_work, dni)
    account = await add_account(unit_of_work, store.id, customer.id, cutoff_day, 26)
    product = await add_product(unit_of_work, store.id)
    return CreditSetup(store.id, account.id, product.id, customer.user_id)


async def add_purchase(
    unit_of_work: UnitOfWork,
    setup: CreditSetup,
    purchased_at: datetime = datetime(2026, 10, 15, 12, tzinfo=LIMA),
    mode: PaymentMode = PaymentMode.WEEKLY,
    quantity: int = 4,
    installments_count: int = 4,
    grace_weeks: Sequence[int] = (),
) -> Purchase:
    """Flush a purchase of the setup's product, by default report test N°3 (S/ 400, 4 weeks)."""
    # Registered on the day of the purchase, so its cycle still takes it.
    cycle = await BillingFacade(unit_of_work).get_or_open_cycle(
        setup.account_id, purchased_at, purchased_at.astimezone(LIMA).date()
    )
    purchase = Purchase.register(
        store_id=setup.store_id,
        account_id=setup.account_id,
        cycle_id=cycle.cycle_id,
        cycle_payment_date=cycle.payment_date,
        purchased_at=purchased_at,
        purchase_day=purchased_at.astimezone(LIMA).date(),
        mode=mode,
        items=[PurchaseItem(setup.product_id, quantity, Money(Decimal("100.00")))],
        tea=Rate.from_percent(Decimal("75")),
        late_tea=Rate.from_percent(Decimal("90")),
        installments_count=installments_count if mode == PaymentMode.WEEKLY else None,
        max_weeks=4,
        created_by=setup.user_id,
        grace_weeks=grace_weeks,
    )
    await PurchaseRepositoryImpl(unit_of_work.session).add(purchase)
    return purchase


# Every 7 days from the purchase on 15/10/2026, without grace.
DUE_DATES_OF_TEST_3 = [
    date(2026, 10, 22),
    date(2026, 10, 29),
    date(2026, 11, 5),
    date(2026, 11, 12),
]


async def add_payment(
    unit_of_work: UnitOfWork,
    setup: CreditSetup,
    *,
    installment_id: int | None = None,
    purchase_id: int | None = None,
) -> int:
    """Flush a payment of zero to reference when marking an installment or purchase as paid."""
    zero = Money(Decimal(0))
    payment = Payment(
        store_id=setup.store_id,
        account_id=setup.account_id,
        kind=PaymentKind.INSTALLMENT if installment_id else PaymentKind.SINGLE_DATE_EARLY,
        paid_on=date(2026, 12, 3),
        breakdown=PaymentBreakdown(zero, zero, zero),
        created_by=setup.user_id,
        installment_id=installment_id,
        purchase_id=purchase_id,
    )
    await PaymentRepositoryImpl(unit_of_work.session).add(payment)
    assert payment.id is not None
    return payment.id
