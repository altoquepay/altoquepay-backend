from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.credit.domain.model.aggregates.purchase import (
    InstallmentStatus,
    Purchase,
    PurchaseStatus,
)
from app.credit.domain.repositories.purchase_repository import (
    InstallmentEntry,
    PurchaseFilter,
    PurchaseRepository,
)
from app.credit.infrastructure.persistence.mappers import (
    copy_payments_to_model,
    installment_to_domain,
    to_domain,
    to_model,
)
from app.credit.infrastructure.persistence.models import InstallmentModel, PurchaseModel
from app.shared.infrastructure.config import get_settings


def start_of_business_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=ZoneInfo(get_settings().app_timezone))


INSTALLMENT_ROWS = select(InstallmentModel, PurchaseModel.id, PurchaseModel.store_customer_id).join(
    PurchaseModel, InstallmentModel.purchase_id == PurchaseModel.id
)


def to_entries(rows) -> list[InstallmentEntry]:
    return [
        InstallmentEntry(installment_to_domain(model), purchase_id, account_id)
        for model, purchase_id, account_id in rows
    ]


class PurchaseRepositoryImpl(PurchaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, purchase_id: int) -> Purchase | None:
        model = await self._session.get(PurchaseModel, purchase_id)
        return to_domain(model) if model else None

    async def find_by_installment(self, installment_id: int) -> Purchase | None:
        model = await self._session.scalar(
            select(PurchaseModel)
            .join(InstallmentModel, InstallmentModel.purchase_id == PurchaseModel.id)
            .where(InstallmentModel.id == installment_id)
        )
        return to_domain(model) if model else None

    async def add(self, purchase: Purchase) -> None:
        model = to_model(purchase)
        self._session.add(model)
        await self._session.flush()
        purchase.id = model.id
        for installment, installment_model in zip(
            purchase.installments, model.installments, strict=True
        ):
            installment.id = installment_model.id

    async def update(self, purchase: Purchase) -> None:
        if purchase.id is None:
            raise ValueError("Only a stored purchase can be updated.")
        model = await self._session.get_one(PurchaseModel, purchase.id)
        copy_payments_to_model(purchase, model)
        await self._session.flush()

    async def list_active_by_account(self, account_id: int) -> list[Purchase]:
        return await self._list(
            select(PurchaseModel).where(
                PurchaseModel.store_customer_id == account_id,
                PurchaseModel.status == PurchaseStatus.ACTIVE.value,
            )
        )

    async def list_by_account(self, account_id: int) -> list[Purchase]:
        return await self._list(
            select(PurchaseModel)
            .where(PurchaseModel.store_customer_id == account_id)
            .order_by(PurchaseModel.purchased_at.desc(), PurchaseModel.id.desc())
        )

    async def list_by_cycle(self, cycle_id: int) -> list[Purchase]:
        return await self._list(
            select(PurchaseModel)
            .where(PurchaseModel.billing_cycle_id == cycle_id)
            .order_by(PurchaseModel.purchased_at, PurchaseModel.id)
        )

    async def list_page(
        self, store_id: int, purchase_filter: PurchaseFilter, offset: int, size: int
    ) -> tuple[list[Purchase], int]:
        query = select(PurchaseModel).where(PurchaseModel.store_id == store_id)
        if purchase_filter.account_id is not None:
            query = query.where(PurchaseModel.store_customer_id == purchase_filter.account_id)
        if purchase_filter.mode is not None:
            query = query.where(PurchaseModel.mode == purchase_filter.mode.value)
        if purchase_filter.from_date is not None:
            query = query.where(
                PurchaseModel.purchased_at >= start_of_business_day(purchase_filter.from_date)
            )
        if purchase_filter.to_date is not None:
            next_day = purchase_filter.to_date + timedelta(days=1)
            query = query.where(PurchaseModel.purchased_at < start_of_business_day(next_day))
        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        purchases = await self._list(
            query.order_by(PurchaseModel.purchased_at.desc(), PurchaseModel.id.desc())
            .offset(offset)
            .limit(size)
        )
        return purchases, total or 0

    async def list_installments(
        self,
        store_id: int,
        status: InstallmentStatus | None,
        due_before: date | None,
        today: date,
        offset: int,
        size: int,
    ) -> tuple[list[InstallmentEntry], int]:
        query = INSTALLMENT_ROWS.where(PurchaseModel.store_id == store_id)
        if status == InstallmentStatus.OVERDUE:
            query = query.where(
                InstallmentModel.status == InstallmentStatus.PENDING.value,
                InstallmentModel.due_date < today,
            )
        elif status == InstallmentStatus.PENDING:
            query = query.where(
                InstallmentModel.status == InstallmentStatus.PENDING.value,
                InstallmentModel.due_date >= today,
            )
        elif status is not None:
            query = query.where(InstallmentModel.status == status.value)
        if due_before is not None:
            query = query.where(InstallmentModel.due_date <= due_before)
        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self._session.execute(
            query.order_by(InstallmentModel.due_date, InstallmentModel.id)
            .offset(offset)
            .limit(size)
        )
        return to_entries(rows), total or 0

    async def list_installments_due(
        self, account_id: int, from_date: date, to_date: date
    ) -> list[InstallmentEntry]:
        rows = await self._session.execute(
            INSTALLMENT_ROWS.where(
                PurchaseModel.store_customer_id == account_id,
                InstallmentModel.status == InstallmentStatus.PENDING.value,
                InstallmentModel.due_date.between(from_date, to_date),
            ).order_by(InstallmentModel.due_date, InstallmentModel.id)
        )
        return to_entries(rows)

    async def find_installment(self, installment_id: int) -> InstallmentEntry | None:
        rows = await self._session.execute(
            INSTALLMENT_ROWS.where(InstallmentModel.id == installment_id)
        )
        entries = to_entries(rows)
        return entries[0] if entries else None

    async def _list(self, query: Select) -> list[Purchase]:
        return [to_domain(model) for model in await self._session.scalars(query)]
