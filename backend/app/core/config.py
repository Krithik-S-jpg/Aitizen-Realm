"""Configuration settings for Aitizen Realm.

Uses pydantic-settings to manage environment variables and configurations.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings managed via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Aitizen Realm"
    DEBUG: bool = False
    DEFAULT_TICK_RATE: float = 1.0
    LOG_LEVEL: str = "INFO"

    # World configurations
    CHUNK_SIZE: int = 16


settings = Settings()
