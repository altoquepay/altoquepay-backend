"""Application settings loaded from environment variables and .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:4200"
    app_timezone: str = "America/Lima"

    @property
    def cors_origins_list(self) -> list[str]:
        """Returns a list of CORS origins from the comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Returns the application settings, cached for performance."""
    return Settings()  # pyright: ignore[reportCallIssue]
