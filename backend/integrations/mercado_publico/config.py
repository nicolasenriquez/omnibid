from __future__ import annotations

from dataclasses import dataclass

from backend.core.config import Settings

DEFAULT_BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico"


@dataclass(frozen=True)
class MercadoPublicoSettings:
    enabled: bool = False
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 30.0
    retry_budget: int = 2
    daily_request_limit: int = 10000
    cache_ttl_seconds: int = 900

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.strip().rstrip("/")


def validate_settings(settings: MercadoPublicoSettings) -> None:
    if settings.timeout_seconds <= 0:
        raise ValueError("MERCADO_PUBLICO_TIMEOUT_SECONDS must be > 0")
    if settings.retry_budget < 0:
        raise ValueError("MERCADO_PUBLICO_RETRY_BUDGET must be >= 0")
    if settings.daily_request_limit < 1:
        raise ValueError("MERCADO_PUBLICO_DAILY_REQUEST_LIMIT must be >= 1")
    if settings.cache_ttl_seconds < 0:
        raise ValueError("MERCADO_PUBLICO_CACHE_TTL_SECONDS must be >= 0")

    if not settings.enabled:
        return

    if not settings.api_key.strip():
        raise ValueError("MERCADO_PUBLICO_API_ENABLED=true requires MERCADO_PUBLICO_API_KEY")
    if not settings.base_url.strip():
        raise ValueError("MERCADO_PUBLICO_BASE_URL must be set when API sync is enabled")


def from_app_settings(settings: Settings) -> MercadoPublicoSettings:
    return MercadoPublicoSettings(
        enabled=settings.mercado_publico_api_enabled,
        api_key=settings.mercado_publico_api_key,
        base_url=settings.mercado_publico_base_url,
        timeout_seconds=settings.mercado_publico_timeout_seconds,
        retry_budget=settings.mercado_publico_retry_budget,
        daily_request_limit=settings.mercado_publico_daily_request_limit,
        cache_ttl_seconds=settings.mercado_publico_cache_ttl_seconds,
    )
