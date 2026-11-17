"""Caps the sign-in attempts of each IP, so a script cannot guess passwords or tie up Argon2."""

import time
from collections.abc import Callable

from fastapi import Request

from app.shared.domain.errors import BusinessError

MAXIMUM_ATTEMPTS = 20
WINDOW_SECONDS = 15 * 60
# Past this many IPs, the ones without recent attempts are forgotten, so memory stays bounded.
TRACKED_IPS_BEFORE_SWEEP = 10_000


def too_many_attempts() -> BusinessError:
    return BusinessError(
        "TOO_MANY_ATTEMPTS",
        "Too many sign-in attempts from this connection. Try again in 15 minutes.",
        status=429,
    )


class SignInAttempts:
    """Counts every attempt, right or wrong, before the password is checked.

    Counting before the check stops a burst of parallel attempts, and counting the right ones
    keeps someone with an account of their own from resetting the count by signing in.
    """

    def __init__(
        self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._attempts: dict[str, list[float]] = {}

    def register(self, ip: str) -> None:
        """Count an attempt of the IP, or raise TOO_MANY_ATTEMPTS (429) if it used them all."""
        now = self._clock()
        if len(self._attempts) > TRACKED_IPS_BEFORE_SWEEP:
            self._forget_idle(now)
        recent = [moment for moment in self._attempts.get(ip, []) if now - moment < self._window]
        if len(recent) >= self._limit:
            self._attempts[ip] = recent
            raise too_many_attempts()
        self._attempts[ip] = [*recent, now]

    def clear(self) -> None:
        self._attempts.clear()

    def _forget_idle(self, now: float) -> None:
        self._attempts = {
            ip: moments
            for ip, moments in self._attempts.items()
            if now - moments[-1] < self._window
        }


# shortcut: the count lives in this process and trusts the IP Uvicorn sees; with several
# workers or replicas, keep it in the database or Redis.
sign_in_attempts = SignInAttempts(MAXIMUM_ATTEMPTS, WINDOW_SECONDS)


async def limit_sign_in_attempts(request: Request) -> None:
    sign_in_attempts.register(request.client.host if request.client else "unknown")
