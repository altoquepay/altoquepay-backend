"""The one-time code a store hands a customer, who redeems it to see that store in their portal."""

import hashlib
import secrets
from datetime import datetime

from app.customers.domain.model.aggregates.store_customer import StoreCustomer
from app.shared.domain.errors import BusinessError

# Capital letters and digits that cannot be mistaken for each other when read aloud.
ACCESS_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ACCESS_CODE_LENGTH = 10


def generate_access_code() -> str:
    """Return a random code that a store administrator can dictate to a customer."""
    return "".join(secrets.choice(ACCESS_CODE_ALPHABET) for _ in range(ACCESS_CODE_LENGTH))


def hash_access_code(code: str) -> str:
    """Return what is kept of a code. It is typed by hand, so case, spaces and hyphens pass."""
    typed = code.replace(" ", "").replace("-", "").upper()
    # The code is random and short-lived, so a fast hash is enough: there is nothing to brute force.
    return hashlib.sha256(typed.encode()).hexdigest()


def invalid_access_code() -> BusinessError:
    # One answer for a wrong DNI, a wrong code and an expired one, so it reveals none of them.
    return BusinessError(
        "INVALID_ACCESS_CODE",
        "The access code is invalid or has expired. Ask the store for a new one.",
        field="code",
    )


def store_not_trusted() -> BusinessError:
    return BusinessError(
        "STORE_NOT_TRUSTED",
        "This store cannot restore your access. Ask for the code at a store you already see "
        "in your portal, or contact AlToque Pay support.",
        field="code",
        status=403,
    )


def redeemed_account(accounts: list[StoreCustomer], code: str, now: datetime) -> StoreCustomer:
    """Return the account, among those of one person, whose store issued the code."""
    code_hash = hash_access_code(code)
    for account in accounts:
        if account.accepts(code_hash, now):
            return account
    raise invalid_access_code()


def restoring_account(accounts: list[StoreCustomer], code: str, now: datetime) -> StoreCustomer:
    """Return the account whose code sets the person's password without a session.

    Any store activates a person who trusts none yet; after that, only a trusted store may.
    """
    account = redeemed_account(accounts, code, now)
    if not account.portal_trusted and any(other.portal_trusted for other in accounts):
        raise store_not_trusted()
    return account
