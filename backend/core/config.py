from functools import lru_cache
from pathlib import Path
import tempfile
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}
DOCKER_DATABASE_HOSTS = {"db", "db_test"}
TEST_DATABASE_SUFFIX = "_test"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="app-chilecompra", alias="APP_NAME")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Default values keep static type checkers happy; runtime validation below
    # still fails fast if either setting is missing or empty.
    database_url: str = Field(default="", alias="DATABASE_URL")
    test_database_url: str = Field(default="", alias="TEST_DATABASE_URL")

    dataset_root: Path | None = Field(default=None, alias="DATASET_ROOT")
    manual_upload_root: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "omnibid-manual-uploads",
        alias="MANUAL_UPLOAD_ROOT",
    )
    manual_upload_max_bytes: int = Field(
        default=800 * 1024 * 1024,
        alias="MANUAL_UPLOAD_MAX_BYTES",
    )


def database_runtime_family(database_url: str) -> str:
    host = (urlparse(database_url.strip()).hostname or "").lower()
    if host in LOCAL_DATABASE_HOSTS:
        return "host"
    if host in DOCKER_DATABASE_HOSTS:
        return "docker"
    return "other"


def database_name(database_url: str) -> str:
    parsed = urlparse(database_url.strip())
    name = parsed.path.lstrip("/")
    if "?" in name:
        name = name.split("?", 1)[0]
    return name


def validate_database_runtime_contract(database_url: str, test_database_url: str) -> None:
    normalized_database_url = database_url.strip()
    normalized_test_database_url = test_database_url.strip()

    if not normalized_database_url:
        raise ValueError("DATABASE_URL is not set.")
    if not normalized_test_database_url:
        raise ValueError("TEST_DATABASE_URL is not set.")
    if normalized_database_url == normalized_test_database_url:
        raise ValueError("TEST_DATABASE_URL must differ from DATABASE_URL")

    database_family = database_runtime_family(normalized_database_url)
    test_family = database_runtime_family(normalized_test_database_url)
    if database_family != test_family and "other" not in {database_family, test_family}:
        raise ValueError("DATABASE_URL and TEST_DATABASE_URL must not mix host and Docker runtime families")

    runtime_database_name = database_name(normalized_database_url).lower()
    if runtime_database_name.endswith(TEST_DATABASE_SUFFIX):
        raise ValueError("DATABASE_URL must not target a test database")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    validate_database_runtime_contract(settings.database_url, settings.test_database_url)
    return settings
