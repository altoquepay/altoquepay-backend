from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.domain.model.aggregates.product import Product
from app.catalog.domain.repositories.product_repository import ProductFilter, ProductRepository
from app.catalog.infrastructure.persistence.mappers import copy_to_model, to_domain
from app.catalog.infrastructure.persistence.models import ProductModel


def escape_like(text: str) -> str:
    """Make % and _ in a search match themselves instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def filtered(query: Select, store_id: int, product_filter: ProductFilter) -> Select:
    query = query.where(ProductModel.store_id == store_id)
    if product_filter.active is not None:
        query = query.where(ProductModel.is_active == product_filter.active)
    search = (product_filter.search or "").strip()
    if search:
        pattern = f"%{escape_like(search)}%"
        query = query.where(
            or_(
                ProductModel.code.ilike(pattern, escape="\\"),
                ProductModel.description.ilike(pattern, escape="\\"),
            )
        )
    return query


class ProductRepositoryImpl(ProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, product_id: int) -> Product | None:
        model = await self._session.get(ProductModel, product_id)
        return to_domain(model) if model else None

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

    async def code_taken(self, store_id: int, code: str, except_id: int | None = None) -> bool:
        same_code = exists().where(ProductModel.store_id == store_id, ProductModel.code == code)
        if except_id is not None:
            same_code = same_code.where(ProductModel.id != except_id)
        return bool(await self._session.scalar(select(same_code)))

    async def list_page(
        self, store_id: int, product_filter: ProductFilter, offset: int, size: int
    ) -> tuple[list[Product], int]:
        total = await self._session.scalar(
            filtered(select(func.count()).select_from(ProductModel), store_id, product_filter)
        )
        models = await self._session.scalars(
            filtered(select(ProductModel), store_id, product_filter)
            .order_by(ProductModel.code, ProductModel.id)
            .offset(offset)
            .limit(size)
        )
        return [to_domain(model) for model in models], total or 0

    async def add(self, product: Product) -> None:
        model = copy_to_model(product, ProductModel())
        self._session.add(model)
        await self._session.flush()
        product.id = model.id

    async def update(self, product: Product) -> None:
        if product.id is None:
            raise ValueError("Only a stored product can be updated.")
        model = await self._session.get_one(ProductModel, product.id)
        copy_to_model(product, model)
        await self._session.flush()
