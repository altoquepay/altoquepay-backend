"""What reporting reads from each context. The answers are the DTOs of their facades."""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.billing.interfaces.acl.billing_facade import CycleStatement, PaymentSummary
from app.credit.interfaces.acl.credit_facade import InstallmentSummary, PurchaseSummary
from app.customers.interfaces.acl.customers_facade import AccountSummary, CreditTerms
from app.regulation.interfaces.acl.regulation_facade import CurrentCap
from app.stores.interfaces.acl.stores_facade import StoreSummary


class CustomerAccounts(ABC):
    @abstractmethod
    async def customer_of_user(self, user_id: int) -> int:
        """Raise NOT_FOUND (404) if the user is not a registered customer."""

    @abstractmethod
    async def accounts_of_person(self, customer_id: int) -> list[AccountSummary]: ...

    @abstractmethod
    async def accounts_of_store(self, store_id: int) -> list[AccountSummary]: ...

    @abstractmethod
    async def terms(self, account_id: int) -> CreditTerms: ...

    @abstractmethod
    async def active_count(self, store_id: int) -> int: ...


class StoreDirectory(ABC):
    @abstractmethod
    async def summary(self, store_id: int) -> StoreSummary: ...


class CreditReader(ABC):
    @abstractmethod
    async def outstanding_principal(self, account_id: int) -> Decimal:
        """Return the unpaid single date amounts plus the principal of unpaid installments."""

    @abstractmethod
    async def installments_due(
        self, account_id: int, from_date: date, to_date: date
    ) -> list[InstallmentSummary]:
        """Return the pending and overdue installments due within the inclusive range."""

    @abstractmethod
    async def purchases(self, account_id: int) -> list[PurchaseSummary]:
        """Return the purchases of an account, most recent first."""

    @abstractmethod
    async def purchase(self, purchase_id: int) -> PurchaseSummary: ...


class BillingReader(ABC):
    @abstractmethod
    async def statement(self, account_id: int, year: int, month: int) -> CycleStatement | None: ...

    @abstractmethod
    async def payments(self, account_id: int) -> list[PaymentSummary]:
        """Return the payments of an account, most recent first."""


class RateCaps(ABC):
    @abstractmethod
    async def in_force(self, on_date: date) -> CurrentCap | None:
        """Return the BCRP cap in force on the date, or None if none is registered."""
