"""Configuration settings for Aitizen Realm.

Uses pydantic-settings to manage environment variables and configurations.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings managed via environment variables."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8", extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Aitizen Realm"
    DEBUG: bool = False
    DEFAULT_TICK_RATE: float = 1.0
    LOCAL_RECOVERY_ENABLED: bool = False
    LOCAL_RECOVERY_INTERVAL_TICKS: int = 300
    LOCAL_RECOVERY_PATH: Path = Path(__file__).resolve().parents[2] / ".local-state" / "recovery.json.gz"
    LOG_LEVEL: str = "INFO"

    # World configurations
    CHUNK_SIZE: int = 16
    LLM_CITIZEN_ID: str = ""
    OLLAMA_MODEL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: SecretStr = SecretStr("")
    CHECKPOINT_ADMIN_TOKEN: SecretStr = SecretStr("")


settings = Settings()
