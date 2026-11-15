from abc import ABC, abstractmethod


class StoreAdministrators(ABC):
    """Creates the administrator of a store, answered by the iam context."""

    @abstractmethod
    async def create(self, email: str, full_name: str, password: str, store_id: int) -> int:
        """Create the administrator without committing and return its user id."""
