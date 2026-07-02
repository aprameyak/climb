from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    storage_dir: Path = Path("./data")
    max_image_size_mb: int = 20
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    log_level: str = "INFO"
    app_version: str = "1.0.0"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def profiles_dir(self) -> Path:
        return self.storage_dir / "profiles"

    @property
    def analyses_dir(self) -> Path:
        return self.storage_dir / "analyses"


@lru_cache
def get_settings() -> Settings:
    return Settings()
