from abc import ABC, abstractmethod


class StoreDirectory(ABC):
    """What billing needs to know about stores, answered by the stores context."""

    @abstractmethod
    async def business_name(self, store_id: int) -> str: ...
