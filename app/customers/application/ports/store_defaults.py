from abc import ABC, abstractmethod

from app.shared.domain.value_objects import CreditConditions


class StoreDefaults(ABC):
    """The conditions a store gives when it sets none, answered by the stores context."""

    @abstractmethod
    async def get(self, store_id: int) -> CreditConditions: ...
