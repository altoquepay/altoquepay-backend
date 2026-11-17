from abc import ABC, abstractmethod

from app.shared.domain.value_objects import CreditConditions


class StoreDirectory(ABC):
    """What the customers context asks the stores context."""

    @abstractmethod
    async def get(self, store_id: int) -> CreditConditions:
        """Return the conditions the store gives when it sets none."""

    @abstractmethod
    async def is_store_active(self, store_id: int) -> bool: ...
