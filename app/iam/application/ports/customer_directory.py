from abc import ABC, abstractmethod
from datetime import datetime


class CustomerDirectory(ABC):
    """What iam needs from customers, answered by the customers context."""

    @abstractmethod
    async def get_customer_id(self, user_id: int) -> int:
        """Return the person (customers.id) behind a customer user."""

    @abstractmethod
    async def redeem_access_code(self, dni: str, code: str, now: datetime) -> int:
        """Spend the access code a store handed to the person and return their user.

        Raises INVALID_ACCESS_CODE (422) if the DNI and the code do not match a code in force.
        """
