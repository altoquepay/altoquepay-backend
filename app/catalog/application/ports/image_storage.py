from abc import ABC, abstractmethod


class ImageStorage(ABC):
    @abstractmethod
    async def save(self, name: str, content: bytes) -> str:
        """Keep the image under that name and return the URL the frontend loads it from."""

    @abstractmethod
    async def delete(self, url: str) -> None:
        """Remove an image saved here. Do nothing for other URLs or missing files."""
