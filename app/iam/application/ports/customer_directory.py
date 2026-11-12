from abc import ABC, abstractmethod


class CustomerDirectory(ABC):
    """What iam needs to know about customers, answered by the customers context."""

    @abstractmethod
    async def get_customer_id(self, user_id: int) -> int:
        """Return the person (customers.id) behind a customer user."""
