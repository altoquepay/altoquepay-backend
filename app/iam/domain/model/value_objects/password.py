from app.shared.domain.errors import BusinessError

PASSWORD_MINIMUM_LENGTH = 8
# Bounded so a huge password cannot make hashing slow on purpose.
PASSWORD_MAXIMUM_LENGTH = 128


def ensure_valid_password(password: str, field: str = "password") -> None:
    """Reject a password a user wants to set if it is too short or too long."""
    if not PASSWORD_MINIMUM_LENGTH <= len(password) <= PASSWORD_MAXIMUM_LENGTH:
        raise BusinessError(
            "INVALID_PASSWORD",
            f"The password must have between {PASSWORD_MINIMUM_LENGTH} "
            f"and {PASSWORD_MAXIMUM_LENGTH} characters.",
            field=field,
        )
