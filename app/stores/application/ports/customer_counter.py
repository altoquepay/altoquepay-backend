from abc import ABC, abstractmethod


class CustomerCounter(ABC):
    """Counts the customers of a store, answered by the customers context."""

    @abstractmethod
    async def count(self, store_id: int) -> int:
        """Return the number of active customer accounts of the store."""
