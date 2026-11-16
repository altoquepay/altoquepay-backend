from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.domain.model.aggregates.product import Product
from app.catalog.domain.repositories.product_repository import ProductRepository
from app.catalog.infrastructure.persistence.mappers import to_domain, to_model
from app.catalog.infrastructure.persistence.models import ProductModel


class ProductRepositoryImpl(ProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_active(self, store_id: int, ids: set[int]) -> list[Product]:
        if not ids:
            return []
        models = await self._session.scalars(
            select(ProductModel).where(
                ProductModel.store_id == store_id,
                ProductModel.id.in_(ids),
                ProductModel.is_active,
            )
        )
        return [to_domain(model) for model in models]

    async def add(self, product: Product) -> None:
        model = to_model(product)
        self._session.add(model)
        await self._session.flush()
        product.id = model.id
