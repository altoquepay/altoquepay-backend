"""A person who buys on credit, in one store or several, with one user to see their accounts."""

from dataclasses import dataclass

from app.shared.domain.value_objects import Dni


@dataclass
class Customer:
    """Only the DNI and the user are shared by the person's stores.

    Each store keeps the names and contact data it typed in its own account, so no store sees
    or changes what another one wrote.
    """

    dni: Dni
    user_id: int
    id: int | None = None
