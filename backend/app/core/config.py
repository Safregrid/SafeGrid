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

    # --- Regional risk grid (docs/RISK_MODEL.md § 4.1) ----------------------
    # The pilot region is CONFIG, not code: repointing SafeGrid at a different
    # community later must be an environment variable, never a code change.
    #
    # WORKING ASSUMPTION — not a confirmed decision. The defaults are a ~33 km
    # box around Gokak (Belagavi district), chosen only because the KSDMA action
    # plan lists Gokak as a Very High flood-risk area. The guide has not
    # confirmed the pilot village. Override in .env once it is agreed.
    grid_cell_size_deg: float = 0.1  # ~11 km = Open-Meteo's model resolution; no invented precision
    grid_region_name: str = "gokak-pilot"
    grid_min_lat: float = 16.0
    grid_min_lon: float = 74.7
    grid_max_lat: float = 16.3
    grid_max_lon: float = 75.0

    grid_window_hours: int = 24  # peak-hour scoring window (P2's DEFAULT_WINDOW_HOURS)
    # Refresh cadence for the scheduled runner. Must stay BELOW P4's
    # GRID_CELL_TTL_SECONDS (3h) or every served cell reads as stale immediately.
    grid_run_minutes: int = 120
    # Whether FastAPI starts the refresh loop at startup. Disabled in tests
    # (tests/conftest.py) so a test session never makes a real Open-Meteo call.
    grid_scheduler_enabled: bool = True


settings = Settings()
