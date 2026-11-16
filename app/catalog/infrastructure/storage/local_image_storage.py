import asyncio
from pathlib import Path

from app.catalog.application.ports.image_storage import ImageStorage

# app/main.py serves MEDIA_DIR under this path.
MEDIA_URL_PREFIX = "/media"
PRODUCTS_FOLDER = "products"


class LocalImageStorage(ImageStorage):
    """Keeps images on the server's disk, under MEDIA_DIR/products.

    shortcut: a container's disk is lost on every redeploy, so images vanish then; move them
    to a bucket (Azure Blob Storage) before production, keeping this port.
    """

    def __init__(self, media_dir: Path) -> None:
        self._media_dir = media_dir

    async def save(self, name: str, content: bytes) -> str:
        path = self._media_dir / PRODUCTS_FOLDER / name
        await asyncio.to_thread(self._write, path, content)
        return f"{MEDIA_URL_PREFIX}/{PRODUCTS_FOLDER}/{name}"

    async def delete(self, url: str) -> None:
        prefix = f"{MEDIA_URL_PREFIX}/{PRODUCTS_FOLDER}/"
        if not url.startswith(prefix):
            return
        path = self._media_dir / PRODUCTS_FOLDER / url.removeprefix(prefix)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
