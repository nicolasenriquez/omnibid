from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
from collections.abc import Mapping
from typing import Any, Literal, Sequence, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.models.operational import PipelineRun, PipelineRunStep

from backend.pipeline.extract.mp_api_client import MercadoPublicoClient
from backend.pipeline.load.mp_api_store import PersistedNoticeBatch, persist_notice_batch, reserve_request_budget

SyncMode = Literal["active-discovery", "rolling-window", "detail-by-codigo"]

DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE = "mercado_publico_api_notice"

STEP_NAME_BY_MODE: dict[SyncMode, str] = {
    "active-discovery": "mp_api_discovery_active",
    "rolling-window": "mp_api_rolling_refresh",
    "detail-by-codigo": "mp_api_detail_enrichment",
}


@dataclass(frozen=True)
class SyncSummary:
    mode: SyncMode
    requests: int
    notices_seen: int
    notices_skipped_missing_external_notice_code: int
    snapshots_upserted: int
    snapshots_inserted: int
    snapshots_updated: int
    notices_with_description: int = 0
    notices_missing_description: int = 0
    notices_with_buyer_region: int = 0
    notices_missing_buyer_region: int = 0
    notices_with_items: int = 0
    notices_missing_items: int = 0
    items_seen: int = 0
    items_persisted: int = 0
    detail_calls_made: int = 0
    detail_calls_failed: int = 0


def _snapshot_payload_id(snapshot: Any) -> UUID | None:
    payload_id = snapshot.payload_id
    if isinstance(payload_id, UUID):
        return payload_id
    return None


def _snapshot_request_id(snapshot: Any) -> UUID | None:
    request_id = snapshot.request_id
    if isinstance(request_id, UUID):
        return request_id
    return None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def rolling_window_dates(*, anchor_day: date, window_days: int) -> list[date]:
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    return [anchor_day.fromordinal(anchor_day.toordinal() - offset) for offset in range(window_days)]


def create_sync_run(
    session: Session,
    *,
    mode: SyncMode,
    requested_by: str = "local_cli",
    run_parameters: Mapping[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[PipelineRun, PipelineRunStep]:
    started_at = _utc_now()
    parameters_payload = dict(run_parameters or {})
    run = PipelineRun(
        run_key=f"mercado-publico-api:{mode}:{started_at.isoformat()}",
        dataset_type=DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE,
        provider="mercado_publico",
        run_mode=mode,
        requested_by=requested_by,
        status="running",
        started_at=started_at,
        run_parameters_json=parameters_payload,
        run_stats_json={
            "final_status": "running",
            "requested_by": requested_by,
            "mode": mode,
        },
        config=config or {},
    )
    session.add(run)
    session.flush()

    step = PipelineRunStep(
        run_id=run.id,
        step_name=STEP_NAME_BY_MODE[mode],
        status="running",
        started_at=started_at,
    )
    session.add(step)
    session.flush()
    return run, step


def mark_sync_run_completed(
    *,
    run: PipelineRun,
    step: PipelineRunStep,
    summary: SyncSummary,
) -> None:
    finished_at = _utc_now()
    run_any = cast(Any, run)
    step_any = cast(Any, step)
    run_config_source = cast(Mapping[str, Any] | None, run_any.config)
    run_config = dict(run_config_source) if run_config_source is not None else {}
    run_any.status = "completed"
    run_any.finished_at = finished_at
    run_any.error_summary = None
    run_any.provider = "mercado_publico"
    run_any.run_mode = summary.mode
    run_any.config = {
        **run_config,
        "sync_summary": {
            "mode": summary.mode,
            "requests": summary.requests,
            "notices_seen": summary.notices_seen,
            "notices_skipped_missing_external_notice_code": summary.notices_skipped_missing_external_notice_code,
            "snapshots_upserted": summary.snapshots_upserted,
            "snapshots_inserted": summary.snapshots_inserted,
            "snapshots_updated": summary.snapshots_updated,
            "notices_with_description": summary.notices_with_description,
            "notices_missing_description": summary.notices_missing_description,
            "notices_with_buyer_region": summary.notices_with_buyer_region,
            "notices_missing_buyer_region": summary.notices_missing_buyer_region,
            "notices_with_items": summary.notices_with_items,
            "notices_missing_items": summary.notices_missing_items,
            "items_seen": summary.items_seen,
            "items_persisted": summary.items_persisted,
            "detail_calls_made": summary.detail_calls_made,
            "detail_calls_failed": summary.detail_calls_failed,
        },
    }
    run_any.run_stats_json = {
        "final_status": "succeeded",
        "mode": summary.mode,
        "requests": summary.requests,
        "notices_seen": summary.notices_seen,
        "notices_skipped_missing_external_notice_code": summary.notices_skipped_missing_external_notice_code,
        "snapshots_upserted": summary.snapshots_upserted,
        "snapshots_inserted": summary.snapshots_inserted,
        "snapshots_updated": summary.snapshots_updated,
        "notices_with_description": summary.notices_with_description,
        "notices_missing_description": summary.notices_missing_description,
        "notices_with_buyer_region": summary.notices_with_buyer_region,
        "notices_missing_buyer_region": summary.notices_missing_buyer_region,
        "notices_with_items": summary.notices_with_items,
        "notices_missing_items": summary.notices_missing_items,
        "items_seen": summary.items_seen,
        "items_persisted": summary.items_persisted,
        "detail_calls_made": summary.detail_calls_made,
        "detail_calls_failed": summary.detail_calls_failed,
    }
    step_any.status = "completed"
    step_any.finished_at = finished_at
    step_any.rows_in = summary.requests
    step_any.rows_out = summary.snapshots_upserted
    step_any.rows_rejected = max(summary.notices_seen - summary.snapshots_upserted, 0)
    step_any.error_details = {
        "notices_skipped_missing_external_notice_code": summary.notices_skipped_missing_external_notice_code,
        "snapshots_upserted": summary.snapshots_upserted,
        "snapshots_inserted": summary.snapshots_inserted,
        "snapshots_updated": summary.snapshots_updated,
    }


def mark_sync_run_failed(
    *,
    run: PipelineRun,
    step: PipelineRunStep,
    error_message: str,
) -> None:
    finished_at = _utc_now()
    run_any = cast(Any, run)
    step_any = cast(Any, step)
    run_any.status = "failed"
    run_any.finished_at = finished_at
    run_any.error_summary = error_message[:4000]
    run_any.run_stats_json = {
        "final_status": "failed",
        "error_message": error_message[:4000],
    }
    step_any.status = "failed"
    step_any.finished_at = finished_at
    step_any.error_details = {"error": error_message[:4000]}


def _lock_key_to_bigint(lock_key: str) -> int:
    digest = hashlib.sha256(lock_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False) - (1 << 63)


def _acquire_scoped_lock(session: Session, *, lock_key: str) -> int:
    lock_token = _lock_key_to_bigint(lock_key)
    acquired = session.execute(
        sa.text("SELECT pg_try_advisory_lock(:lock_token)"),
        {"lock_token": lock_token},
    ).scalar_one()
    if acquired is not True:
        raise RuntimeError(f"scoped advisory lock not available for key={lock_key}")
    return lock_token


def _release_scoped_lock(session: Session, *, lock_token: int) -> None:
    session.execute(
        sa.text("SELECT pg_advisory_unlock(:lock_token)"),
        {"lock_token": lock_token},
    )


def _resolve_safe_url(client: MercadoPublicoClient, *, params: dict[str, str]) -> str | None:
    builder = getattr(client, "build_safe_url", None)
    if not callable(builder):
        return None
    return cast(str, builder(endpoint="licitaciones.json", params=params))


def _resolve_daily_limit(client: MercadoPublicoClient) -> int | None:
    settings = getattr(client, "settings", None)
    if settings is None:
        return None
    value = getattr(settings, "daily_request_limit", None)
    if value is None:
        return None
    return int(value)


def _can_use_sql_guards(session: Session) -> bool:
    return hasattr(session, "execute")


def _consume_request_slot(*, consumed_requests: int, max_requests: int | None) -> int:
    if max_requests is None:
        return consumed_requests + 1
    if max_requests < 1:
        raise ValueError("max_requests must be >= 1")
    if consumed_requests >= max_requests:
        raise RuntimeError(f"max requests reached before next upstream call: limit={max_requests}")
    return consumed_requests + 1


def execute_sync_mode(
    *,
    session: Session,
    client: MercadoPublicoClient,
    pipeline_run_id: UUID,
    mode: SyncMode,
    anchor_day: date | None = None,
    window_days: int = 4,
    estado: str | None = None,
    codigos: Sequence[str] | None = None,
    max_requests: int | None = None,
) -> SyncSummary:
    responses: list[Any] = []
    sql_guard_enabled = _can_use_sql_guards(session)
    daily_limit = _resolve_daily_limit(client)
    consumed_requests = 0
    if mode == "active-discovery":
        params = client.build_active_discovery_params()
        safe_url = _resolve_safe_url(client, params=params)
        requested_at = _utc_now()
        lock_token: int | None = None
        if sql_guard_enabled:
            lock_token = _acquire_scoped_lock(
                session,
                lock_key=f"mercado_publico:active_discovery:{_utc_now().date().isoformat()}",
            )
        try:
            consumed_requests = _consume_request_slot(
                consumed_requests=consumed_requests,
                max_requests=max_requests,
            )
            if sql_guard_enabled and daily_limit is not None:
                reserve_request_budget(
                    session,
                    pipeline_run_id=pipeline_run_id,
                    source_system="mercado_publico",
                    endpoint_name="licitaciones.json",
                    resource_type="licitacion",
                    resource_key="estado=activas",
                    request_params=params,
                    request_url_safe=safe_url,
                    daily_limit=daily_limit,
                    requested_at=requested_at,
                )
            raw_payload, response = client.fetch_active_discovery_with_raw()
            persisted = persist_notice_batch(
                session,
                pipeline_run_id=pipeline_run_id,
                endpoint_name="licitaciones.json",
                resource_type="licitacion",
                resource_key="estado=activas",
                request_params=params,
                request_url_safe=safe_url,
                source_mode=mode,
                requested_at=requested_at,
                payload=raw_payload,
                notices=response.notices,
            )
            responses.append(response)
            return _summary_from_batches(mode=mode, responses=[response], persisted_batches=[persisted])
        finally:
            if lock_token is not None:
                _release_scoped_lock(session, lock_token=lock_token)

    if mode == "rolling-window":
        effective_anchor = anchor_day or _utc_now().date()
        days = rolling_window_dates(anchor_day=effective_anchor, window_days=window_days)
        rolling_batches: list[PersistedNoticeBatch] = []
        for day in days:
            consumed_requests = _consume_request_slot(
                consumed_requests=consumed_requests,
                max_requests=max_requests,
            )
            params = client.build_rolling_window_params(day=day, estado=estado)
            safe_url = _resolve_safe_url(client, params=params)
            requested_at = _utc_now()
            estado_label = (estado or "all").strip() or "all"
            rolling_lock_token: int | None = None
            if sql_guard_enabled:
                rolling_lock_token = _acquire_scoped_lock(
                    session,
                    lock_key=(
                        "mercado_publico:rolling_window:"
                        f"{day.isoformat()}:window={window_days}:estado={estado_label}"
                    ),
                )
            try:
                if sql_guard_enabled and daily_limit is not None:
                    reserve_request_budget(
                        session,
                        pipeline_run_id=pipeline_run_id,
                        source_system="mercado_publico",
                        endpoint_name="licitaciones.json",
                        resource_type="licitacion",
                        resource_key=f"fecha={params['fecha']}",
                        request_params=params,
                        request_url_safe=safe_url,
                        daily_limit=daily_limit,
                        requested_at=requested_at,
                    )
                raw_payload, response = client.fetch_rolling_window_with_raw(day=day, estado=estado)
                batch = persist_notice_batch(
                    session,
                    pipeline_run_id=pipeline_run_id,
                    endpoint_name="licitaciones.json",
                    resource_type="licitacion",
                    resource_key=f"fecha={params['fecha']}",
                    request_params=params,
                    request_url_safe=safe_url,
                    source_mode=mode,
                    requested_at=requested_at,
                    payload=raw_payload,
                    notices=response.notices,
                )
                responses.append(response)
                rolling_batches.append(batch)
            finally:
                if rolling_lock_token is not None:
                    _release_scoped_lock(session, lock_token=rolling_lock_token)
        return _summary_from_batches(mode=mode, responses=responses, persisted_batches=rolling_batches)

    if mode == "detail-by-codigo":
        if codigos is None or len(codigos) == 0:
            raise ValueError("detail-by-codigo mode requires at least one codigo")
        detail_batches: list[PersistedNoticeBatch] = []
        for codigo in codigos:
            normalized_codigo = codigo.strip()
            if normalized_codigo == "":
                continue
            consumed_requests = _consume_request_slot(
                consumed_requests=consumed_requests,
                max_requests=max_requests,
            )
            params = client.build_detail_by_codigo_params(codigo=normalized_codigo)
            safe_url = _resolve_safe_url(client, params=params)
            requested_at = _utc_now()
            detail_lock_token: int | None = None
            if sql_guard_enabled:
                detail_lock_token = _acquire_scoped_lock(
                    session,
                    lock_key=f"mercado_publico:detail_by_codigo:{normalized_codigo}",
                )
            try:
                if sql_guard_enabled and daily_limit is not None:
                    reserve_request_budget(
                        session,
                        pipeline_run_id=pipeline_run_id,
                        source_system="mercado_publico",
                        endpoint_name="licitaciones.json",
                        resource_type="licitacion",
                        resource_key=normalized_codigo,
                        request_params=params,
                        request_url_safe=safe_url,
                        daily_limit=daily_limit,
                        requested_at=requested_at,
                    )
                raw_payload, response = client.fetch_detail_by_codigo_with_raw(codigo=normalized_codigo)
                batch = persist_notice_batch(
                    session,
                    pipeline_run_id=pipeline_run_id,
                    endpoint_name="licitaciones.json",
                    resource_type="licitacion",
                    resource_key=normalized_codigo,
                    request_params=params,
                    request_url_safe=safe_url,
                    source_mode=mode,
                    requested_at=requested_at,
                    payload=raw_payload,
                    notices=response.notices,
                )
                responses.append(response)
                detail_batches.append(batch)
            finally:
                if detail_lock_token is not None:
                    _release_scoped_lock(session, lock_token=detail_lock_token)
        return _summary_from_batches(mode=mode, responses=responses, persisted_batches=detail_batches)

    raise ValueError(f"unsupported sync mode: {mode}")


def _summary_from_batches(
    *,
    mode: SyncMode,
    responses: Sequence[Any],
    persisted_batches: Sequence[PersistedNoticeBatch],
) -> SyncSummary:
    notices_seen = sum(len(response.notices) for response in responses)
    notices_skipped = sum(
        int(getattr(batch, "notices_skipped_missing_external_notice_code", 0) or 0)
        for batch in persisted_batches
    )
    snapshots_upserted = sum(
        int(
            getattr(
                batch,
                "snapshots_upserted",
                getattr(batch, "snapshots_inserted", 0),
            )
            or 0
        )
        for batch in persisted_batches
    )
    snapshots_inserted = sum(
        int(getattr(batch, "snapshots_inserted", 0) or 0)
        for batch in persisted_batches
    )
    snapshots_updated = sum(
        int(getattr(batch, "snapshots_updated", 0) or 0)
        for batch in persisted_batches
    )
    items_seen_total = sum(
        int(getattr(batch, "items_seen", 0) or 0) for batch in persisted_batches
    )
    items_persisted_total = sum(
        int(getattr(batch, "items_persisted", 0) or 0) for batch in persisted_batches
    )

    notices_with_description = 0
    notices_with_buyer_region = 0
    notices_with_items = 0
    for response in responses:
        for notice in getattr(response, "notices", []) or []:
            if getattr(notice, "description", None):
                notices_with_description += 1
            comprador = getattr(notice, "comprador", None)
            if comprador is not None and getattr(comprador, "region_unidad", None):
                notices_with_buyer_region += 1
            items = getattr(notice, "items", None)
            if items is not None and getattr(items, "listado", None):
                notices_with_items += 1

    detail_calls_made = len(responses) if mode == "detail-by-codigo" else 0

    return SyncSummary(
        mode=mode,
        requests=len(responses),
        notices_seen=notices_seen,
        notices_skipped_missing_external_notice_code=notices_skipped,
        snapshots_upserted=snapshots_upserted,
        snapshots_inserted=snapshots_inserted,
        snapshots_updated=snapshots_updated,
        notices_with_description=notices_with_description,
        notices_missing_description=notices_seen - notices_with_description,
        notices_missing_buyer_region=notices_seen - notices_with_buyer_region,
        notices_with_buyer_region=notices_with_buyer_region,
        notices_with_items=notices_with_items,
        notices_missing_items=notices_seen - notices_with_items,
        items_seen=items_seen_total,
        items_persisted=items_persisted_total,
        detail_calls_made=detail_calls_made,
        detail_calls_failed=0,
    )
