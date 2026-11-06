"""Tests for the validation of the application settings."""

import pytest
from pydantic import ValidationError

from app.shared.infrastructure.config import JWT_SECRET_MINIMUM_LENGTH, Settings


def settings_with_jwt_secret(jwt_secret: str) -> Settings:
    return Settings(_env_file=None, database_url="postgresql://unused", jwt_secret=jwt_secret)


def test_placeholder_jwt_secret_of_the_example_file_is_rejected():
    with pytest.raises(ValidationError):
        settings_with_jwt_secret("change-me")


def test_jwt_secret_of_the_minimum_length_is_accepted():
    secret = "x" * JWT_SECRET_MINIMUM_LENGTH
    assert settings_with_jwt_secret(secret).jwt_secret == secret
