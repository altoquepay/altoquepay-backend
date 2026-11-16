from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.shared.domain.value_objects import Money, Rate


@dataclass(frozen=True)
class AccountTerms:
    store_id: int
    credit_limit: Money
    tea: Rate
    late_tea: Rate
    max_weeks: int
    is_active: bool


class CreditAccounts(ABC):
    """The credit conditions of a customer account, answered by the customers context."""

    @abstractmethod
    async def lock_and_read(self, account_id: int) -> AccountTerms:
        """Lock the account until the transaction ends, then read its terms.

        The lock keeps two purchases at once from both passing the credit limit check.
        Raises NOT_FOUND (404) if the account does not exist.
        """
