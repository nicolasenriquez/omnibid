from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from collections.abc import Mapping
from typing import Any, Literal, Sequence, cast
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.operational import PipelineRun, PipelineRunStep

from .client import MercadoPublicoClient
from .store import PersistedNoticeBatch, persist_notice_batch

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
    config: dict[str, Any] | None = None,
) -> tuple[PipelineRun, PipelineRunStep]:
    started_at = _utc_now()
    run = PipelineRun(
        run_key=f"mercado-publico-api:{mode}:{started_at.isoformat()}",
        dataset_type=DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE,
        status="running",
        started_at=started_at,
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
        },
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
    step_any.status = "failed"
    step_any.finished_at = finished_at
    step_any.error_details = {"error": error_message[:4000]}


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
) -> SyncSummary:
    responses: list[Any] = []
    if mode == "active-discovery":
        response = client.fetch_active_discovery()
        persisted = persist_notice_batch(
            session,
            pipeline_run_id=pipeline_run_id,
            endpoint_name="licitaciones.json",
            resource_type="licitacion",
            resource_key="estado=activas",
            request_params=client.build_active_discovery_params(),
            payload=response.model_dump(by_alias=True, exclude_none=False),
            notices=response.notices,
        )
        responses.append(response)
        return _summary_from_batches(mode=mode, responses=[response], persisted_batches=[persisted])

    if mode == "rolling-window":
        effective_anchor = anchor_day or _utc_now().date()
        days = rolling_window_dates(anchor_day=effective_anchor, window_days=window_days)
        rolling_batches: list[PersistedNoticeBatch] = []
        for day in days:
            response = client.fetch_rolling_window(day=day, estado=estado)
            params = client.build_rolling_window_params(day=day, estado=estado)
            batch = persist_notice_batch(
                session,
                pipeline_run_id=pipeline_run_id,
                endpoint_name="licitaciones.json",
                resource_type="licitacion",
                resource_key=f"fecha={params['fecha']}",
                request_params=params,
                payload=response.model_dump(by_alias=True, exclude_none=False),
                notices=response.notices,
            )
            responses.append(response)
            rolling_batches.append(batch)
        return _summary_from_batches(mode=mode, responses=responses, persisted_batches=rolling_batches)

    if mode == "detail-by-codigo":
        if codigos is None or len(codigos) == 0:
            raise ValueError("detail-by-codigo mode requires at least one codigo")
        detail_batches: list[PersistedNoticeBatch] = []
        for codigo in codigos:
            normalized_codigo = codigo.strip()
            if normalized_codigo == "":
                continue
            response = client.fetch_detail_by_codigo(codigo=normalized_codigo)
            params = client.build_detail_by_codigo_params(codigo=normalized_codigo)
            batch = persist_notice_batch(
                session,
                pipeline_run_id=pipeline_run_id,
                endpoint_name="licitaciones.json",
                resource_type="licitacion",
                resource_key=normalized_codigo,
                request_params=params,
                payload=response.model_dump(by_alias=True, exclude_none=False),
                notices=response.notices,
            )
            responses.append(response)
            detail_batches.append(batch)
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
    return SyncSummary(
        mode=mode,
        requests=len(responses),
        notices_seen=notices_seen,
        notices_skipped_missing_external_notice_code=notices_skipped,
        snapshots_upserted=snapshots_upserted,
        snapshots_inserted=snapshots_inserted,
        snapshots_updated=snapshots_updated,
    )
