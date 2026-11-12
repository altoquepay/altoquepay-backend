from abc import ABC, abstractmethod


class StoreDirectory(ABC):
    """What iam needs to know about stores, answered by the stores context."""

    @abstractmethod
    async def is_store_active(self, store_id: int) -> bool: ...
