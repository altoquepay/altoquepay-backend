import secrets

from app.catalog.application.ports.image_storage import ImageStorage
from app.catalog.application.query_services.product_query_service import ProductQueryService
from app.catalog.domain.model.aggregates.product import Product, ProductDetails
from app.catalog.domain.repositories.product_repository import ProductRepository
from app.catalog.domain.services.product_image import image_extension
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork


class ProductCommandService:
    def __init__(
        self, products: ProductRepository, images: ImageStorage, unit_of_work: UnitOfWork
    ) -> None:
        self._products = products
        self._images = images
        self._unit_of_work = unit_of_work
        self._query = ProductQueryService(products)

    async def create(self, store_id: int, details: ProductDetails) -> Product:
        product = details.new_product(store_id)
        await self._ensure_code_free(store_id, product.code)
        await self._products.add(product)
        await self._unit_of_work.commit()
        return product

    async def update(self, store_id: int, product_id: int, details: ProductDetails) -> Product:
        product = await self._query.get(store_id, product_id)
        product.update(details)
        await self._ensure_code_free(store_id, product.code, except_id=product_id)
        await self._products.update(product)
        await self._unit_of_work.commit()
        return product

    async def deactivate(self, store_id: int, product_id: int) -> Product:
        """Stop selling the product. Purchases already registered keep their copied price."""
        product = await self._query.get(store_id, product_id)
        product.deactivate()
        await self._products.update(product)
        await self._unit_of_work.commit()
        return product

    async def reactivate(self, store_id: int, product_id: int) -> Product:
        """Sell the product again, with the details and prices it has now."""
        product = await self._query.get(store_id, product_id)
        product.reactivate()
        await self._products.update(product)
        await self._unit_of_work.commit()
        return product

    async def change_image(self, store_id: int, product_id: int, content: bytes) -> Product:
        """Save a JPEG, PNG or WebP image of up to 2 MB and replace the previous one."""
        product = await self._query.get(store_id, product_id)
        extension = image_extension(content)
        # A new random name each time, so browsers never show a cached old image.
        name = f"{store_id}/{product_id}-{secrets.token_hex(8)}.{extension}"
        previous_url = product.image_url
        product.change_image(await self._images.save(name, content))
        await self._products.update(product)
        if previous_url is not None:
            await self._images.delete(previous_url)
        await self._unit_of_work.commit()
        return product

    async def _ensure_code_free(
        self, store_id: int, code: str, except_id: int | None = None
    ) -> None:
        # shortcut: two simultaneous saves can both pass this check, and the unique constraint
        # then rejects one with a 500; map IntegrityError to 409 if that ever happens.
        if await self._products.code_taken(store_id, code, except_id):
            raise BusinessError(
                "PRODUCT_CODE_TAKEN",
                "Another product of the store already has this code.",
                field="code",
                status=409,
            )
