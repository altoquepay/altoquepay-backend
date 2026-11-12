import secrets

# Letters and digits that cannot be mistaken for each other when read aloud or handwritten.
TEMPORARY_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
TEMPORARY_PASSWORD_LENGTH = 10


def generate_temporary_password() -> str:
    """Return a random password that a store administrator can dictate to a customer."""
    return "".join(
        secrets.choice(TEMPORARY_PASSWORD_ALPHABET) for _ in range(TEMPORARY_PASSWORD_LENGTH)
    )
