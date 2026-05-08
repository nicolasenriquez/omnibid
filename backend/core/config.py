from functools import lru_cache
from pathlib import Path
import tempfile
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}
DOCKER_DATABASE_HOSTS = {"db", "db_test"}
TEST_DATABASE_SUFFIX = "_test"
MERCADO_PUBLICO_DEFAULT_BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico"


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
    ingestion_queue_max_attempts: int = Field(
        default=2,
        alias="INGESTION_QUEUE_MAX_ATTEMPTS",
    )
    ingestion_queue_retry_delay_seconds: int = Field(
        default=120,
        alias="INGESTION_QUEUE_RETRY_DELAY_SECONDS",
    )
    ingestion_queue_poll_seconds: float = Field(
        default=5.0,
        alias="INGESTION_QUEUE_POLL_SECONDS",
    )
    ingestion_dead_letter_retention_days: int = Field(
        default=30,
        alias="INGESTION_DEAD_LETTER_RETENTION_DAYS",
    )
    mercado_publico_api_enabled: bool = Field(default=False, alias="MERCADO_PUBLICO_API_ENABLED")
    mercado_publico_api_key: str = Field(default="", alias="MERCADO_PUBLICO_API_KEY")
    mercado_publico_base_url: str = Field(
        default=MERCADO_PUBLICO_DEFAULT_BASE_URL,
        alias="MERCADO_PUBLICO_BASE_URL",
    )
    mercado_publico_timeout_seconds: float = Field(default=30.0, alias="MERCADO_PUBLICO_TIMEOUT_SECONDS")
    mercado_publico_retry_budget: int = Field(default=2, alias="MERCADO_PUBLICO_RETRY_BUDGET")
    mercado_publico_daily_request_limit: int = Field(
        default=10000,
        alias="MERCADO_PUBLICO_DAILY_REQUEST_LIMIT",
    )
    mercado_publico_cache_ttl_seconds: int = Field(
        default=900,
        alias="MERCADO_PUBLICO_CACHE_TTL_SECONDS",
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


def validate_ingestion_queue_contract(settings: Settings) -> None:
    if settings.ingestion_queue_max_attempts < 1:
        raise ValueError("INGESTION_QUEUE_MAX_ATTEMPTS must be >= 1")
    if settings.ingestion_queue_retry_delay_seconds <= 0:
        raise ValueError("INGESTION_QUEUE_RETRY_DELAY_SECONDS must be > 0")
    if settings.ingestion_queue_poll_seconds <= 0:
        raise ValueError("INGESTION_QUEUE_POLL_SECONDS must be > 0")
    if settings.ingestion_dead_letter_retention_days < 1:
        raise ValueError("INGESTION_DEAD_LETTER_RETENTION_DAYS must be >= 1")


def validate_mercado_publico_contract(settings: Settings) -> None:
    if settings.mercado_publico_timeout_seconds <= 0:
        raise ValueError("MERCADO_PUBLICO_TIMEOUT_SECONDS must be > 0")
    if settings.mercado_publico_retry_budget < 0:
        raise ValueError("MERCADO_PUBLICO_RETRY_BUDGET must be >= 0")
    if settings.mercado_publico_daily_request_limit < 1:
        raise ValueError("MERCADO_PUBLICO_DAILY_REQUEST_LIMIT must be >= 1")
    if settings.mercado_publico_cache_ttl_seconds < 0:
        raise ValueError("MERCADO_PUBLICO_CACHE_TTL_SECONDS must be >= 0")

    if not settings.mercado_publico_api_enabled:
        return

    if settings.mercado_publico_api_key.strip() == "":
        raise ValueError("MERCADO_PUBLICO_API_ENABLED=true requires MERCADO_PUBLICO_API_KEY")
    if settings.mercado_publico_base_url.strip() == "":
        raise ValueError("MERCADO_PUBLICO_BASE_URL must be set when API sync is enabled")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    validate_database_runtime_contract(settings.database_url, settings.test_database_url)
    validate_ingestion_queue_contract(settings)
    validate_mercado_publico_contract(settings)
    return settings
