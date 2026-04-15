"""Application configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PKOS_", extra="ignore")

    app_name: str = "pkos-collector"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/pkos",
    )
    data_dir: Path = Field(default=Path("./data"))
    init_db_on_startup: bool = True
    embedding_dimensions: int = 64
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: float = 30.0
    deepseek_max_tokens: int = 800


settings = Settings()
