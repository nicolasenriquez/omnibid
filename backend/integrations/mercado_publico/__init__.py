"""Mercado Publico integration primitives."""

from .client import MercadoPublicoClient, redact_query_params
from .config import MercadoPublicoSettings, from_app_settings, validate_settings
from .enums import LicitacionEstadoCode
from .errors import (
    MercadoPublicoConfigError,
    MercadoPublicoContractDriftError,
    MercadoPublicoIntegrationError,
    MercadoPublicoRateLimitError,
    MercadoPublicoRequestError,
)
from .rate_limit import DailyRequestBudget, retry_backoff_seconds
from .schemas import LicitacionNotice, LicitacionesResponse, parse_licitaciones_response
from .store import (
    PersistedNoticeBatch,
    canonical_request_params,
    compute_payload_hash,
    compute_request_hash,
    persist_notice_batch,
)
from .sync import (
    DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE,
    STEP_NAME_BY_MODE,
    SyncMode,
    SyncSummary,
    create_sync_run,
    execute_sync_mode,
    mark_sync_run_completed,
    mark_sync_run_failed,
    rolling_window_dates,
)

__all__ = [
    "DailyRequestBudget",
    "LicitacionEstadoCode",
    "LicitacionNotice",
    "LicitacionesResponse",
    "MercadoPublicoClient",
    "MercadoPublicoConfigError",
    "MercadoPublicoContractDriftError",
    "MercadoPublicoIntegrationError",
    "MercadoPublicoRateLimitError",
    "MercadoPublicoRequestError",
    "MercadoPublicoSettings",
    "PersistedNoticeBatch",
    "STEP_NAME_BY_MODE",
    "SyncMode",
    "SyncSummary",
    "canonical_request_params",
    "compute_payload_hash",
    "compute_request_hash",
    "create_sync_run",
    "DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE",
    "execute_sync_mode",
    "from_app_settings",
    "mark_sync_run_completed",
    "mark_sync_run_failed",
    "parse_licitaciones_response",
    "persist_notice_batch",
    "redact_query_params",
    "rolling_window_dates",
    "retry_backoff_seconds",
    "validate_settings",
]
