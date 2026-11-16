from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.domain.model.aggregates.payment import Payment
from app.billing.domain.repositories.payment_repository import PaymentFilter, PaymentRepository
from app.billing.infrastructure.persistence.mappers import payment_to_domain, payment_to_model
from app.billing.infrastructure.persistence.models import PaymentModel

MOST_RECENT_FIRST = (PaymentModel.paid_on.desc(), PaymentModel.id.desc())


def filtered(query: Select, store_id: int, payment_filter: PaymentFilter) -> Select:
    query = query.where(PaymentModel.store_id == store_id)
    if payment_filter.account_id is not None:
        query = query.where(PaymentModel.store_customer_id == payment_filter.account_id)
    if payment_filter.kind is not None:
        query = query.where(PaymentModel.kind == payment_filter.kind.value)
    if payment_filter.from_date is not None:
        query = query.where(PaymentModel.paid_on >= payment_filter.from_date)
    if payment_filter.to_date is not None:
        query = query.where(PaymentModel.paid_on <= payment_filter.to_date)
    return query


class PaymentRepositoryImpl(PaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_account(self, account_id: int) -> list[Payment]:
        models = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.store_customer_id == account_id)
            .order_by(*MOST_RECENT_FIRST)
        )
        return [payment_to_domain(model) for model in models]

    async def list_page(
        self, store_id: int, payment_filter: PaymentFilter, offset: int, size: int
    ) -> tuple[list[Payment], int]:
        total = await self._session.scalar(
            filtered(select(func.count()).select_from(PaymentModel), store_id, payment_filter)
        )
        models = await self._session.scalars(
            filtered(select(PaymentModel), store_id, payment_filter)
            .order_by(*MOST_RECENT_FIRST)
            .offset(offset)
            .limit(size)
        )
        return [payment_to_domain(model) for model in models], total or 0

    async def add(self, payment: Payment) -> None:
        model = payment_to_model(payment)
        self._session.add(model)
        await self._session.flush()
        # The database sets the creation time, so read it back.
        await self._session.refresh(model, ["created_at"])
        payment.id = model.id
        payment.created_at = model.created_at
