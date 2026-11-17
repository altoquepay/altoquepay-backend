from abc import ABC, abstractmethod


class ImageStorage(ABC):
    @abstractmethod
    async def save(self, name: str, content: bytes) -> str:
        """Keep the image under that name and return the URL the frontend loads it from."""

    @abstractmethod
    async def delete(self, url: str) -> None:
        """Remove an image saved here. Do nothing for other URLs or missing files."""

    @abstractmethod
    async def load(self, name: str) -> bytes | None:
        """Return the image saved under that name, or None if there is none."""
