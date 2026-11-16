from abc import ABC, abstractmethod
from datetime import date

from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap


class BcrpCapRepository(ABC):
    @abstractmethod
    async def find_in_force(self, on_date: date) -> BcrpCap | None: ...

    @abstractmethod
    async def exists_overlapping(self, valid_from: date, valid_to: date) -> bool: ...

    @abstractmethod
    async def list_all(self) -> list[BcrpCap]:
        """Return every cap, the most recent first."""

    @abstractmethod
    async def add(self, cap: BcrpCap) -> None:
        """Store a new cap and set its id."""
