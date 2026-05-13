"""Mercado Publico integration primitives."""

from backend.pipeline.extract.mp_api_config import MercadoPublicoSettings, from_app_settings, validate_settings
from backend.pipeline.extract.mp_api_enums import LicitacionEstadoCode
from backend.pipeline.extract.mp_api_errors import (
    MercadoPublicoConfigError,
    MercadoPublicoContractDriftError,
    MercadoPublicoIntegrationError,
    MercadoPublicoRateLimitError,
    MercadoPublicoRequestError,
)
from backend.pipeline.extract.mp_api_rate_limit import DailyRequestBudget, retry_backoff_seconds
from backend.pipeline.extract.mp_api_schemas import LicitacionNotice, LicitacionesResponse, parse_licitaciones_response
from backend.pipeline.extract.mp_api_client import MercadoPublicoClient, redact_query_params
from backend.pipeline.load.mp_api_store import (
    PersistedNoticeBatch,
    canonical_request_params,
    compute_payload_hash,
    compute_request_hash,
    persist_notice_batch,
)
from backend.pipeline.orchestration.sync import (
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
