from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.application.ports.image_storage import ImageStorage
from app.catalog.infrastructure.persistence.models import ProductImageModel

# The catalog's media router serves the images under this path.
MEDIA_URL_PREFIX = "/media/products/"


class DatabaseImageStorage(ImageStorage):
    """Keeps images in PostgreSQL, in the same transaction as the product that shows them."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, name: str, content: bytes) -> str:
        self._session.add(ProductImageModel(name=name, content=content))
        await self._session.flush()
        return f"{MEDIA_URL_PREFIX}{name}"

    async def delete(self, url: str) -> None:
        if url.startswith(MEDIA_URL_PREFIX):
            await self._session.execute(
                delete(ProductImageModel).where(
                    ProductImageModel.name == url.removeprefix(MEDIA_URL_PREFIX)
                )
            )

    async def load(self, name: str) -> bytes | None:
        return await self._session.scalar(
            select(ProductImageModel.content).where(ProductImageModel.name == name)
        )
