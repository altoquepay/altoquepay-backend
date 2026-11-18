"""Caps the sign-in and reset requests of each IP, so a script cannot guess passwords,
tie up Argon2 or flood an inbox with reset emails.
"""

from fastapi import Request

from app.iam.domain.model.aggregates.user import normalize_username
from app.iam.infrastructure.persistence.attempt_counter import count_attempt
from app.shared.domain.errors import BusinessError

MAXIMUM_ATTEMPTS = 20
RESET_EMAILS_PER_ACCOUNT = 3


def too_many_attempts() -> BusinessError:
    return BusinessError(
        "TOO_MANY_ATTEMPTS",
        "Too many attempts from this connection. Try again in 15 minutes.",
        status=429,
    )


async def limit_sign_in_attempts(request: Request) -> None:
    """Count the attempt of the IP, right or wrong, before the password is checked.

    Counting before the check stops a burst of parallel attempts, and counting the right ones
    keeps someone with an account of their own from resetting the count by signing in.
    """
    ip = request.client.host if request.client else "unknown"
    if await count_attempt(f"ip:{ip}") > MAXIMUM_ATTEMPTS:
        raise too_many_attempts()


async def reset_email_allowed(email: str) -> bool:
    """Count a reset request for the email and say whether it may still get a reset email.

    It counts every email, with an account or not, so the limit never shows which ones exist.
    """
    return await count_attempt(f"reset:{normalize_username(email)}") <= RESET_EMAILS_PER_ACCOUNT
