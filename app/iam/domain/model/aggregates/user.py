"""Someone who signs in to AlToque Pay, with the role that decides what they may do."""

from dataclasses import dataclass

from app.iam.domain.model.value_objects.email import Email
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Dni, Role

FULL_NAME_MAXIMUM_LENGTH = 150


def normalize_username(username: str) -> str:
    """Return the username as stored: emails in lowercase, DNIs as they are."""
    return username.strip().lower()


@dataclass
class User:
    """Administrators sign in with their email and customers with their DNI."""

    username: str
    password_hash: str
    role: Role
    store_id: int | None = None
    full_name: str | None = None
    must_change_password: bool = False
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        # Only a store administrator belongs to a store; a customer may buy in several.
        if (self.role == Role.STORE_ADMIN) != (self.store_id is not None):
            raise ValueError("Only a store administrator has a store.")

    @classmethod
    def system_admin(cls, email: Email, password_hash: str) -> "User":
        """The first administrator comes from the settings, so they must pick their own password."""
        return cls(email.value, password_hash, Role.SYSTEM_ADMIN, must_change_password=True)

    @classmethod
    def store_admin(cls, email: Email, full_name: str, password_hash: str, store_id: int) -> "User":
        """The store administrator chose the password while registering the store."""
        full_name = full_name.strip()
        if not full_name or len(full_name) > FULL_NAME_MAXIMUM_LENGTH:
            raise BusinessError(
                "INVALID_FULL_NAME",
                f"The full name must have between 1 and {FULL_NAME_MAXIMUM_LENGTH} characters.",
                field="full_name",
            )
        return cls(email.value, password_hash, Role.STORE_ADMIN, store_id, full_name)

    @classmethod
    def customer(cls, dni: Dni, temporary_password_hash: str) -> "User":
        """The store hands the temporary password to the customer, who must replace it."""
        return cls(dni.value, temporary_password_hash, Role.CUSTOMER, must_change_password=True)

    def change_password(self, password_hash: str) -> None:
        """Set a password the user chose, which lifts the block of a temporary one."""
        self.password_hash = password_hash
        self.must_change_password = False

    def assign_temporary_password(self, password_hash: str) -> None:
        """Set a password someone else will hand over, so the user must replace it."""
        self.password_hash = password_hash
        self.must_change_password = True
