from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.pipeline.extract.mp_api_client import MercadoPublicoClient
from backend.integrations.mercado_publico.sync import (
    DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE,
    STEP_NAME_BY_MODE,
    SyncSummary,
    execute_sync_mode,
    rolling_window_dates,
)
from backend.models.api_source import ApiSourcePayload, ApiSourceRequest
from backend.models.operational import IngestionBatch, PipelineRun, PipelineRunStep, SourceFile
from backend.normalized.mp_api_notice_refresh import (
    select_latest_notice_snapshots,
)
from backend.normalized.mp_api_read_model_bridge import (
    MpApiCanonicalizationSummary,
    MpApiSilverPostprocessSummary,
    canonicalize_mp_api_payloads_to_read_model,
    run_mp_api_silver_postprocess,
    select_detail_enrichment_candidates,
)
from backend.pipeline.extract.file_contracts import normalize_dataset_type
from backend.nlp.runtime import (
    IMPLEMENTED_SOURCE_PROFILE,
    normalize_source_profile,
)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_normalized import process_licitaciones, process_ordenes_compra  # noqa: E402
from scripts.ingest_raw import process_registered_file  # noqa: E402

RAW_CHUNK_SIZE = 5_000
NORMALIZED_FETCH_SIZE = 10_000
NORMALIZED_CHUNK_SIZE = 500
MP_API_CANONICALIZATION_STEP_NAME = "mp_api_payload_canonicalization"
MP_API_SILVER_POSTPROCESS_STEP_NAME = "mp_api_silver_postprocess"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _dict_any(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    return dict(value)


def _source_file_payload_id(snapshot: Any) -> UUID | None:
    payload_id = snapshot.payload_id
    if isinstance(payload_id, UUID):
        return payload_id
    return None


def _source_file_request_id(snapshot: Any) -> UUID | None:
    request_id = snapshot.request_id
    if isinstance(request_id, UUID):
        return request_id
    return None


def _sha256_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _create_pipeline_step(
    session: Session,
    *,
    run_id: Any,
    step_name: str,
) -> PipelineRunStep:
    started_at = _utc_now()
    step = PipelineRunStep(
        run_id=run_id,
        step_name=step_name,
        status="running",
        started_at=started_at,
        error_details={},
    )
    session.add(step)
    session.flush()
    return step


def _mark_pipeline_step_completed(
    step: PipelineRunStep,
    *,
    rows_in: int,
    rows_out: int,
    rows_rejected: int = 0,
    details: dict[str, Any] | None = None,
) -> None:
    step_any = cast(Any, step)
    step_any.status = "completed"
    step_any.finished_at = _utc_now()
    step_any.rows_in = rows_in
    step_any.rows_out = rows_out
    step_any.rows_rejected = rows_rejected
    step_any.error_details = details or {}


def _mark_pipeline_step_failed(step: PipelineRunStep, *, error_message: str) -> None:
    step_any = cast(Any, step)
    step_any.status = "failed"
    step_any.finished_at = _utc_now()
    step_any.error_details = {"error": error_message[:4000]}


def _create_mp_api_daily_pipeline_run(
    session: Session,
    *,
    target_date: date,
    window_days: int,
    estado: str | None,
    refresh_only: bool,
    requested_by: str,
    max_requests: int | None,
) -> PipelineRun:
    started_at = _utc_now()
    run = PipelineRun(
        run_key=f"mercado-publico-api-daily:{target_date.isoformat()}:{started_at.isoformat()}",
        dataset_type=DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE,
        provider="mercado_publico",
        run_mode="daily_notice_silver_refresh",
        requested_by=requested_by,
        status="running",
        started_at=started_at,
        run_parameters_json={
            "target_date": target_date.isoformat(),
            "window_days": window_days,
            "estado": estado,
            "refresh_only": refresh_only,
            "requested_by": requested_by,
            "max_requests": max_requests,
        },
        run_stats_json={
            "final_status": "running",
            "requested_by": requested_by,
            "max_requests": max_requests,
        },
        config={
            "mode": "daily_notice_silver_refresh",
            "target_date": target_date.isoformat(),
            "window_days": window_days,
            "estado": estado,
            "refresh_only": refresh_only,
            "requested_by": requested_by,
            "max_requests": max_requests,
        },
    )
    session.add(run)
    session.flush()
    return run


def _mark_pipeline_run_failed(run: PipelineRun, *, error_message: str) -> None:
    run_any = cast(Any, run)
    run_any.status = "failed"
    run_any.finished_at = _utc_now()
    run_any.error_summary = error_message[:4000]
    run_any.run_stats_json = {
        "final_status": "failed",
        "error_message": error_message[:4000],
    }


def _mark_pipeline_run_completed(
    run: PipelineRun,
    *,
    source_file_id: Any,
    sync_summary: SyncSummary,
    detail_summary: SyncSummary,
    silver_summary: MpApiCanonicalizationSummary,
    postprocess_summary: MpApiSilverPostprocessSummary,
) -> None:
    run_any = cast(Any, run)
    run_config: dict[str, Any] = _dict_any(cast(Mapping[str, Any] | None, run_any.config))
    run_any.config = {
        **run_config,
        "sync_summary": {
            "mode": sync_summary.mode,
            "requests": sync_summary.requests,
            "notices_seen": sync_summary.notices_seen,
            "notices_skipped_missing_external_notice_code": (
                sync_summary.notices_skipped_missing_external_notice_code
            ),
            "snapshots_upserted": sync_summary.snapshots_upserted,
            "snapshots_inserted": sync_summary.snapshots_inserted,
            "snapshots_updated": sync_summary.snapshots_updated,
        },
        "detail_summary": {
            "mode": detail_summary.mode,
            "requests": detail_summary.requests,
            "notices_seen": detail_summary.notices_seen,
            "notices_skipped_missing_external_notice_code": (
                detail_summary.notices_skipped_missing_external_notice_code
            ),
            "snapshots_upserted": detail_summary.snapshots_upserted,
            "snapshots_inserted": detail_summary.snapshots_inserted,
            "snapshots_updated": detail_summary.snapshots_updated,
        },
        "canonicalization_summary": {
            "payload_rows_seen": silver_summary.payload_rows_seen,
            "payload_rows_used": silver_summary.payload_rows_used,
            "notice_candidates": silver_summary.notice_candidates,
            "upserted_notices": silver_summary.upserted_notices,
            "upserted_normalized_licitaciones": silver_summary.upserted_normalized_licitaciones,
            "upserted_normalized_licitacion_items": silver_summary.upserted_normalized_licitacion_items,
            "upserted_normalized_ofertas": silver_summary.upserted_normalized_ofertas,
            "upserted_normalized_suppliers": silver_summary.upserted_normalized_suppliers,
            "upserted_silver_notice": silver_summary.upserted_silver_notice,
            "upserted_silver_notice_line": silver_summary.upserted_silver_notice_line,
            "upserted_silver_bid_submission": silver_summary.upserted_silver_bid_submission,
            "upserted_silver_award_outcome": silver_summary.upserted_silver_award_outcome,
            "upserted_silver_buying_org": silver_summary.upserted_silver_buying_org,
            "upserted_silver_contracting_unit": silver_summary.upserted_silver_contracting_unit,
            "upserted_silver_supplier": silver_summary.upserted_silver_supplier,
            "upserted_silver_category_ref": silver_summary.upserted_silver_category_ref,
            "upserted_silver_supplier_participation": silver_summary.upserted_silver_supplier_participation,
        },
        "silver_postprocess_summary": {
            "notice_purchase_order_links_inserted": (
                postprocess_summary.notice_purchase_order_links_inserted
            ),
        },
        # Backward-compatible summary key used by older operator/reporting surfaces.
        "silver_refresh_summary": {
            "notice_candidates": silver_summary.notice_candidates,
            "upserted_notices": silver_summary.upserted_notices,
        },
        "source_file_id": str(source_file_id),
    }
    run_any.source_file_id = source_file_id
    run_any.status = "completed"
    run_any.finished_at = _utc_now()
    run_any.error_summary = None
    run_any.run_stats_json = {
        "final_status": "succeeded",
        "sync": {
            "mode": sync_summary.mode,
            "requests": sync_summary.requests,
            "notices_seen": sync_summary.notices_seen,
            "notices_skipped_missing_external_notice_code": (
                sync_summary.notices_skipped_missing_external_notice_code
            ),
            "snapshots_upserted": sync_summary.snapshots_upserted,
            "snapshots_inserted": sync_summary.snapshots_inserted,
            "snapshots_updated": sync_summary.snapshots_updated,
        },
        "detail": {
            "mode": detail_summary.mode,
            "requests": detail_summary.requests,
            "notices_seen": detail_summary.notices_seen,
            "notices_skipped_missing_external_notice_code": (
                detail_summary.notices_skipped_missing_external_notice_code
            ),
            "snapshots_upserted": detail_summary.snapshots_upserted,
            "snapshots_inserted": detail_summary.snapshots_inserted,
            "snapshots_updated": detail_summary.snapshots_updated,
        },
        "canonicalization": {
            "payload_rows_seen": silver_summary.payload_rows_seen,
            "payload_rows_used": silver_summary.payload_rows_used,
            "notice_candidates": silver_summary.notice_candidates,
            "upserted_notices": silver_summary.upserted_notices,
            "upserted_normalized_licitaciones": silver_summary.upserted_normalized_licitaciones,
            "upserted_normalized_licitacion_items": silver_summary.upserted_normalized_licitacion_items,
            "upserted_normalized_ofertas": silver_summary.upserted_normalized_ofertas,
            "upserted_normalized_suppliers": silver_summary.upserted_normalized_suppliers,
            "upserted_silver_notice": silver_summary.upserted_silver_notice,
            "upserted_silver_notice_line": silver_summary.upserted_silver_notice_line,
            "upserted_silver_bid_submission": silver_summary.upserted_silver_bid_submission,
            "upserted_silver_award_outcome": silver_summary.upserted_silver_award_outcome,
            "upserted_silver_buying_org": silver_summary.upserted_silver_buying_org,
            "upserted_silver_contracting_unit": silver_summary.upserted_silver_contracting_unit,
            "upserted_silver_supplier": silver_summary.upserted_silver_supplier,
            "upserted_silver_category_ref": silver_summary.upserted_silver_category_ref,
            "upserted_silver_supplier_participation": silver_summary.upserted_silver_supplier_participation,
        },
        "silver_postprocess": {
            "notice_purchase_order_links_inserted": (
                postprocess_summary.notice_purchase_order_links_inserted
            ),
        },
    }


def _serialize_payload_bytes(payload_json: Any) -> int:
    if payload_json is None:
        return 0
    return len(
        json.dumps(payload_json, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    )


def _resolve_rolling_window_days_for_sync(*, window_days: int, max_requests: int | None) -> int:
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    if max_requests is None:
        return window_days

    capped_requests = max(int(max_requests), 1)
    if capped_requests <= 1:
        return 1
    return min(window_days, capped_requests - 1)


def _fetch_payload_rows_by_ids(session: Session, payload_ids: list[Any]) -> list[ApiSourcePayload]:
    if not payload_ids:
        return []
    return cast(
        list[ApiSourcePayload],
        session.execute(sa.select(ApiSourcePayload).where(ApiSourcePayload.id.in_(payload_ids)))
        .scalars()
        .all(),
    )


def _fetch_request_rows_by_ids(session: Session, request_ids: list[Any]) -> list[ApiSourceRequest]:
    if not request_ids:
        return []
    return cast(
        list[ApiSourceRequest],
        session.execute(sa.select(ApiSourceRequest).where(ApiSourceRequest.id.in_(request_ids)))
        .scalars()
        .all(),
    )


def _register_mp_api_snapshot_source_file(
    session: Session,
    *,
    target_date: date,
    window_days: int,
    estado: str | None,
    scope_pipeline_run_id: UUID | None,
    window_dates: list[date],
) -> SourceFile:
    latest_snapshots = select_latest_notice_snapshots(
        session,
        pipeline_run_id=scope_pipeline_run_id,
        window_dates=None if scope_pipeline_run_id is not None else window_dates,
    )
    payload_ids = sorted(
        {
            payload_id
            for snapshot in latest_snapshots
            if (payload_id := _source_file_payload_id(snapshot)) is not None
        }
    )
    request_ids = sorted(
        {
            request_id
            for snapshot in latest_snapshots
            if (request_id := _source_file_request_id(snapshot)) is not None
        }
    )
    payload_rows = _fetch_payload_rows_by_ids(session, payload_ids)
    request_rows = _fetch_request_rows_by_ids(session, request_ids)

    payload_hashes = sorted(
        str(payload.payload_sha256)
        for payload in payload_rows
        if str(payload.payload_sha256 or "").strip() != ""
    )
    request_hashes = sorted(
        str(request.request_hash)
        for request in request_rows
        if str(request.request_hash or "").strip() != ""
    )
    uri = (
        "api://mercado-publico/licitaciones/rolling-window/"
        f"{target_date.isoformat()}?window_days={window_days}&estado={estado or 'all'}"
    )
    hash_basis = {
        "uri": uri,
        "window_dates": [day.isoformat() for day in window_dates],
        "payload_sha256": payload_hashes,
        "request_hashes": request_hashes,
    }
    file_hash_sha256 = _sha256_json(hash_basis)
    file_size_bytes = sum(_serialize_payload_bytes(payload.payload_json) for payload in payload_rows)
    if file_size_bytes < 0:
        file_size_bytes = 0

    existing = session.execute(
        sa.select(SourceFile).where(SourceFile.file_hash_sha256 == file_hash_sha256)
    ).scalar_one_or_none()

    source_meta = {
        "source_kind": "api_snapshot",
        "source_system": "mercado_publico",
        "sync_mode": "rolling-window",
        "target_date": target_date.isoformat(),
        "window_days": window_days,
        "estado": estado,
        "window_dates": [day.isoformat() for day in window_dates],
        "notice_count": len(latest_snapshots),
        "request_count": len(request_hashes),
        "payload_count": len(payload_hashes),
        "request_hashes": request_hashes,
        "payload_sha256": payload_hashes,
        "snapshot_scope": "pipeline_run" if scope_pipeline_run_id is not None else "window_dates",
        "pipeline_run_id": str(scope_pipeline_run_id) if scope_pipeline_run_id is not None else None,
    }
    source_modified_at = max((payload.fetched_at for payload in payload_rows), default=None)

    if existing is not None:
        existing_any = cast(Any, existing)
        existing_meta: dict[str, Any] = _dict_any(cast(Mapping[str, Any] | None, existing_any.source_meta))
        existing_any.file_name = f"mercado-publico-api-notice-{target_date.isoformat()}.json"
        existing_any.file_path = uri
        existing_any.file_size_bytes = file_size_bytes
        existing_any.source_modified_at = source_modified_at
        existing_any.status = "loaded"
        existing_any.source_meta = {
            **existing_meta,
            **source_meta,
        }
        session.flush()
        return existing

    source_file = SourceFile(
        dataset_type=DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE,
        file_name=f"mercado-publico-api-notice-{target_date.isoformat()}.json",
        file_path=uri,
        file_size_bytes=file_size_bytes,
        file_hash_sha256=file_hash_sha256,
        source_modified_at=source_modified_at,
        status="loaded",
        source_meta=source_meta,
    )
    session.add(source_file)
    session.flush()
    return source_file


@dataclass(frozen=True)
class MpApiDailyPipelineSummary:
    run_id: UUID
    source_file_id: UUID
    sync_summary: SyncSummary
    detail_summary: SyncSummary
    silver_summary: MpApiCanonicalizationSummary
    postprocess_summary: MpApiSilverPostprocessSummary


def resolve_normalized_build_processor(dataset_type: str) -> Callable[..., dict[str, Any]]:
    normalized_dataset_type = normalize_dataset_type(dataset_type)
    if normalized_dataset_type == "licitacion":
        return process_licitaciones
    return process_ordenes_compra


def run_registered_raw_ingest(
    session: Session,
    *,
    dataset_type: str,
    source_profile: str = IMPLEMENTED_SOURCE_PROFILE,
    path: Path,
    source_file: SourceFile,
    batch: IngestionBatch,
    run: PipelineRun,
    step: PipelineRunStep,
    expected_rows: int | None = None,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> dict[str, int]:
    normalize_source_profile(source_profile)
    normalized_dataset_type = normalize_dataset_type(dataset_type)
    return process_registered_file(
        session=session,
        dataset_type=normalized_dataset_type,
        path=path,
        source_file=source_file,
        batch=batch,
        run=run,
        step=step,
        chunk_size=RAW_CHUNK_SIZE,
        show_progress=False,
        precount=False,
        expected_rows=expected_rows,
        on_progress=on_progress,
    )


def run_normalized_build(
    session: Session,
    *,
    dataset_type: str,
    source_profile: str = IMPLEMENTED_SOURCE_PROFILE,
    source_file_id: Any,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    normalize_source_profile(source_profile)
    processor = resolve_normalized_build_processor(dataset_type)
    base_kwargs: dict[str, Any] = {
        "session": session,
        "fetch_size": NORMALIZED_FETCH_SIZE,
        "chunk_size": NORMALIZED_CHUNK_SIZE,
        "limit_rows": 0,
        "show_progress": False,
        "start_after_id": 0,
        "source_file_id": source_file_id,
        "debug_telemetry": False,
        "state_checkpoint_every_pages": 1,
        "on_checkpoint": None,
        "on_quality_checkpoint": None,
        "on_progress": on_progress,
    }
    return processor(**base_kwargs)


def run_mp_api_daily_notice_pipeline(
    session: Session,
    *,
    client: MercadoPublicoClient,
    target_date: date,
    window_days: int = 4,
    estado: str | None = None,
    refresh_only: bool = False,
    requested_by: str = "local_cli",
    max_requests: int | None = None,
) -> MpApiDailyPipelineSummary:
    run = _create_mp_api_daily_pipeline_run(
        session,
        target_date=target_date,
        window_days=window_days,
        estado=estado,
        refresh_only=refresh_only,
        requested_by=requested_by,
        max_requests=max_requests,
    )
    rolling_step = _create_pipeline_step(
        session,
        run_id=run.id,
        step_name=STEP_NAME_BY_MODE["rolling-window"],
    )
    detail_step = _create_pipeline_step(
        session,
        run_id=run.id,
        step_name=STEP_NAME_BY_MODE["detail-by-codigo"],
    )
    window_dates = rolling_window_dates(anchor_day=target_date, window_days=window_days)

    try:
        if refresh_only:
            sync_summary = SyncSummary(
                mode="rolling-window",
                requests=0,
                notices_seen=0,
                notices_skipped_missing_external_notice_code=0,
                snapshots_upserted=0,
                snapshots_inserted=0,
                snapshots_updated=0,
            )
            _mark_pipeline_step_completed(
                rolling_step,
                rows_in=0,
                rows_out=0,
                rows_rejected=0,
                details={"skipped": True, "reason": "refresh_only"},
            )
            detail_summary = SyncSummary(
                mode="detail-by-codigo",
                requests=0,
                notices_seen=0,
                notices_skipped_missing_external_notice_code=0,
                snapshots_upserted=0,
                snapshots_inserted=0,
                snapshots_updated=0,
            )
            _mark_pipeline_step_completed(
                detail_step,
                rows_in=0,
                rows_out=0,
                rows_rejected=0,
                details={"skipped": True, "reason": "refresh_only"},
            )
            sync_scope_pipeline_run_id: UUID | None = None
        else:
            rolling_window_days_for_sync = _resolve_rolling_window_days_for_sync(
                window_days=window_days,
                max_requests=max_requests,
            )
            sync_summary = execute_sync_mode(
                session=session,
                client=client,
                pipeline_run_id=UUID(str(run.id)),
                mode="rolling-window",
                anchor_day=target_date,
                window_days=rolling_window_days_for_sync,
                estado=estado,
                max_requests=max_requests,
            )
            _mark_pipeline_step_completed(
                rolling_step,
                rows_in=sync_summary.requests,
                rows_out=sync_summary.snapshots_upserted,
                rows_rejected=max(sync_summary.notices_seen - sync_summary.snapshots_upserted, 0),
                details={
                    "notices_skipped_missing_external_notice_code": (
                        sync_summary.notices_skipped_missing_external_notice_code
                    ),
                    "snapshots_upserted": sync_summary.snapshots_upserted,
                    "snapshots_inserted": sync_summary.snapshots_inserted,
                    "snapshots_updated": sync_summary.snapshots_updated,
                },
            )
            sync_scope_pipeline_run_id = UUID(str(run.id))
            remaining_requests = (
                None
                if max_requests is None
                else max(0, int(max_requests) - int(sync_summary.requests))
            )
            if remaining_requests == 0:
                detail_candidates = select_detail_enrichment_candidates(
                    session,
                    target_date=target_date,
                    pipeline_run_id=sync_scope_pipeline_run_id,
                    backfill_interval_days=7,
                    max_candidates=1,
                )
                detail_summary = SyncSummary(
                    mode="detail-by-codigo",
                    requests=0,
                    notices_seen=0,
                    notices_skipped_missing_external_notice_code=0,
                    snapshots_upserted=0,
                    snapshots_inserted=0,
                    snapshots_updated=0,
                )
                _mark_pipeline_step_completed(
                    detail_step,
                    rows_in=detail_candidates.notice_candidates,
                    rows_out=0,
                    rows_rejected=detail_candidates.notice_candidates,
                    details={
                        "detail_candidates": detail_candidates.detail_candidates,
                        "selected_codes": 0,
                        "skipped": True,
                        "reason": "max_requests_exhausted_by_rolling",
                    },
                )
            else:
                detail_candidates = select_detail_enrichment_candidates(
                    session,
                    target_date=target_date,
                    pipeline_run_id=sync_scope_pipeline_run_id,
                    backfill_interval_days=7,
                    max_candidates=remaining_requests if remaining_requests and remaining_requests > 0 else None,
                )
                if len(detail_candidates.selected_codes) == 0:
                    detail_summary = SyncSummary(
                        mode="detail-by-codigo",
                        requests=0,
                        notices_seen=0,
                        notices_skipped_missing_external_notice_code=0,
                        snapshots_upserted=0,
                        snapshots_inserted=0,
                        snapshots_updated=0,
                    )
                    _mark_pipeline_step_completed(
                        detail_step,
                        rows_in=detail_candidates.notice_candidates,
                        rows_out=0,
                        rows_rejected=detail_candidates.notice_candidates,
                        details={
                            "detail_candidates": detail_candidates.detail_candidates,
                            "selected_codes": 0,
                            "skipped": True,
                            "reason": "no_candidates",
                        },
                    )
                else:
                    detail_summary = execute_sync_mode(
                        session=session,
                        client=client,
                        pipeline_run_id=UUID(str(run.id)),
                        mode="detail-by-codigo",
                        codigos=list(detail_candidates.selected_codes),
                        max_requests=remaining_requests,
                    )
                    _mark_pipeline_step_completed(
                        detail_step,
                        rows_in=detail_candidates.notice_candidates,
                        rows_out=detail_summary.snapshots_upserted,
                        rows_rejected=max(
                            detail_candidates.notice_candidates - detail_summary.snapshots_upserted,
                            0,
                        ),
                        details={
                            "detail_candidates": detail_candidates.detail_candidates,
                            "selected_codes": len(detail_candidates.selected_codes),
                            "requests": detail_summary.requests,
                            "snapshots_upserted": detail_summary.snapshots_upserted,
                            "snapshots_inserted": detail_summary.snapshots_inserted,
                            "snapshots_updated": detail_summary.snapshots_updated,
                        },
                    )

        source_file = _register_mp_api_snapshot_source_file(
            session,
            target_date=target_date,
            window_days=window_days,
            estado=estado,
            scope_pipeline_run_id=sync_scope_pipeline_run_id,
            window_dates=window_dates,
        )
        run_any = cast(Any, run)
        run_any.source_file_id = source_file.id

        canonical_step = _create_pipeline_step(
            session,
            run_id=run.id,
            step_name=MP_API_CANONICALIZATION_STEP_NAME,
        )
        postprocess_step = _create_pipeline_step(
            session,
            run_id=run.id,
            step_name=MP_API_SILVER_POSTPROCESS_STEP_NAME,
        )
        try:
            silver_summary = canonicalize_mp_api_payloads_to_read_model(
                session,
                source_file_id=source_file.id,
                pipeline_run_id=sync_scope_pipeline_run_id,
                window_dates=None if sync_scope_pipeline_run_id is not None else window_dates,
            )
            _mark_pipeline_step_completed(
                canonical_step,
                rows_in=silver_summary.payload_rows_seen,
                rows_out=(
                    silver_summary.upserted_normalized_licitaciones
                    + silver_summary.upserted_normalized_licitacion_items
                    + silver_summary.upserted_normalized_ofertas
                    + silver_summary.upserted_normalized_suppliers
                    + silver_summary.upserted_silver_notice
                    + silver_summary.upserted_silver_notice_line
                    + silver_summary.upserted_silver_bid_submission
                    + silver_summary.upserted_silver_award_outcome
                    + silver_summary.upserted_silver_buying_org
                    + silver_summary.upserted_silver_contracting_unit
                    + silver_summary.upserted_silver_supplier
                    + silver_summary.upserted_silver_category_ref
                    + silver_summary.upserted_silver_supplier_participation
                ),
                rows_rejected=max(silver_summary.payload_rows_seen - silver_summary.payload_rows_used, 0),
                details={
                    "payload_rows_used": silver_summary.payload_rows_used,
                    "notice_candidates": silver_summary.notice_candidates,
                    "upserted_notices": silver_summary.upserted_notices,
                    "upserted_normalized_licitaciones": (
                        silver_summary.upserted_normalized_licitaciones
                    ),
                    "upserted_normalized_licitacion_items": (
                        silver_summary.upserted_normalized_licitacion_items
                    ),
                    "upserted_normalized_ofertas": silver_summary.upserted_normalized_ofertas,
                    "upserted_normalized_suppliers": silver_summary.upserted_normalized_suppliers,
                    "upserted_silver_notice_line": silver_summary.upserted_silver_notice_line,
                    "upserted_silver_bid_submission": silver_summary.upserted_silver_bid_submission,
                    "upserted_silver_award_outcome": silver_summary.upserted_silver_award_outcome,
                },
            )
            postprocess_summary = run_mp_api_silver_postprocess(session)
            _mark_pipeline_step_completed(
                postprocess_step,
                rows_in=silver_summary.upserted_notices,
                rows_out=postprocess_summary.notice_purchase_order_links_inserted,
                rows_rejected=0,
                details={
                    "notice_purchase_order_links_inserted": (
                        postprocess_summary.notice_purchase_order_links_inserted
                    ),
                },
            )
        except Exception as exc:
            canonical_step_any = cast(Any, canonical_step)
            if str(canonical_step_any.status) == "running":
                _mark_pipeline_step_failed(canonical_step, error_message=str(exc))
            postprocess_step_any = cast(Any, postprocess_step)
            if str(postprocess_step_any.status) == "running":
                _mark_pipeline_step_failed(postprocess_step, error_message=str(exc))
            _mark_pipeline_run_failed(run, error_message=str(exc))
            raise

        _mark_pipeline_run_completed(
            run,
            source_file_id=source_file.id,
            sync_summary=sync_summary,
            detail_summary=detail_summary,
            silver_summary=silver_summary,
            postprocess_summary=postprocess_summary,
        )
        return MpApiDailyPipelineSummary(
            run_id=UUID(str(run.id)),
            source_file_id=UUID(str(source_file.id)),
            sync_summary=sync_summary,
            detail_summary=detail_summary,
            silver_summary=silver_summary,
            postprocess_summary=postprocess_summary,
        )
    except Exception as exc:
        rolling_step_any = cast(Any, rolling_step)
        if str(rolling_step_any.status) == "running":
            _mark_pipeline_step_failed(rolling_step, error_message=str(exc))
        detail_step_any = cast(Any, detail_step)
        if str(detail_step_any.status) == "running":
            _mark_pipeline_step_failed(detail_step, error_message=str(exc))
        _mark_pipeline_run_failed(run, error_message=str(exc))
        raise

