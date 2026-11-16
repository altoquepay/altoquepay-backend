"""Application settings loaded from environment variables and .env file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

JWT_SECRET_MINIMUM_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # A short secret makes tokens forgeable, so the application refuses to start with one.
    jwt_secret: str = Field(min_length=JWT_SECRET_MINIMUM_LENGTH)
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:4200"
    app_timezone: str = "America/Lima"
    # The system administrator created at startup if missing. Leave empty to create none.
    first_admin_email: str = ""
    first_admin_password: str = ""
    reset_token_minutes: int = 30
    # Without SMTP_HOST, password reset links are logged instead of emailed.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    frontend_url: str = "http://localhost:4200"
    # Folder for uploaded files such as product images, served under /media.
    media_dir: str = "media"

    @property
    def cors_origins_list(self) -> list[str]:
        """Returns a list of CORS origins from the comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Returns the application settings, cached for performance."""
    return Settings()  # pyright: ignore[reportCallIssue]
