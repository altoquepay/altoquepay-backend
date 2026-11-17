"""Tests for the cap on sign-in attempts per IP."""

import pytest

from app.iam.interfaces.rest import sign_in_attempts as module
from app.iam.interfaces.rest.sign_in_attempts import SignInAttempts
from app.shared.domain.errors import BusinessError


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_each_ip_gets_the_limit_of_attempts_per_window():
    clock = FakeClock()
    attempts = SignInAttempts(limit=3, window_seconds=60, clock=clock)
    for _ in range(3):
        attempts.register("10.0.0.1")

    with pytest.raises(BusinessError) as error:
        attempts.register("10.0.0.1")

    assert (error.value.code, error.value.status) == ("TOO_MANY_ATTEMPTS", 429)
    attempts.register("10.0.0.2")
    clock.now = 60
    attempts.register("10.0.0.1")


def test_idle_ips_are_forgotten_once_many_are_tracked(monkeypatch):
    monkeypatch.setattr(module, "TRACKED_IPS_BEFORE_SWEEP", 2)
    clock = FakeClock()
    attempts = SignInAttempts(limit=3, window_seconds=60, clock=clock)
    for ip in ("10.0.0.1", "10.0.0.2", "10.0.0.3"):
        attempts.register(ip)

    clock.now = 60
    attempts.register("10.0.0.4")

    assert list(attempts._attempts) == ["10.0.0.4"]
