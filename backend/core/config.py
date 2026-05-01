from functools import lru_cache
from pathlib import Path
import tempfile

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="app-chilecompra", alias="APP_NAME")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra",
        alias="DATABASE_URL",
    )

    dataset_root: Path | None = Field(default=None, alias="DATASET_ROOT")
    manual_upload_root: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "omnibid-manual-uploads",
        alias="MANUAL_UPLOAD_ROOT",
    )
    manual_upload_max_bytes: int = Field(
        default=800 * 1024 * 1024,
        alias="MANUAL_UPLOAD_MAX_BYTES",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
