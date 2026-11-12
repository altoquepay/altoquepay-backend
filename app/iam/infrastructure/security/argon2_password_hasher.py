import asyncio
from functools import cache

from pwdlib import PasswordHash

from app.iam.application.ports.password_hasher import PasswordHasher

# Argon2 with the parameters pwdlib recommends.
_argon2 = PasswordHash.recommended()


@cache
def _hash_of_no_user() -> str:
    # Made on first use, since hashing at import would slow down every startup.
    return _argon2.hash("password of no user")


class Argon2PasswordHasher(PasswordHasher):
    """Runs Argon2 in a worker thread, so a slow hash never blocks other requests."""

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(_argon2.hash, password)

    async def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        return await asyncio.to_thread(_argon2.verify_and_update, password, password_hash)

    async def verify_without_user(self, password: str) -> None:
        await asyncio.to_thread(lambda: _argon2.verify(password, _hash_of_no_user()))
