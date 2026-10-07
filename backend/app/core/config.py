"""
Application configuration.

Reads values from environment variables (or a .env file).
Person 1 owns this file.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_env: str = "development"
    log_level: str = "INFO"

    usgs_feed_url: str = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary"
    open_meteo_url: str = "https://api.open-meteo.com/v1"

    # OPEN: database_url is not set until the database is chosen.
    database_url: str | None = None

    # Comma-separated string → list of strings
    allowed_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
