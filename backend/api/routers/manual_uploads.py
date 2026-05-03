from __future__ import annotations

from email.parser import BytesParser
from email.policy import default as email_default_policy
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, cast
from uuid import UUID, uuid4

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.config import Settings, get_settings
from backend.ingestion.manual_uploads import (
    ManualCsvPreflight,
    ManualUploadError,
    build_manual_csv_preflight,
    format_manual_upload_size_limit,
    load_manual_upload_preflight,
    mark_manual_upload_preflight_consumed,
)
from backend.db.session import SessionLocal
from backend.models.normalized import (
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedOrdenCompra,
    NormalizedOrdenCompraItem,
)
from backend.models.operational import IngestionBatch, PipelineRun, PipelineRunStep, SourceFile
from backend.models.raw import RawLicitacion, RawOrdenCompra

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_normalized import process_licitaciones, process_ordenes_compra  # noqa: E402
from scripts.ingest_raw import process_registered_file  # noqa: E402

router = APIRouter(prefix="/uploads/procurement-csv", tags=["manual_uploads"])
DEFAULT_BACKGROUND_TASKS = BackgroundTasks()

DATASET_FIELD_NAME = "dataset_type"
MANUAL_UPLOAD_STEP_NAME = "manual_upload_registration"


def _count_rows(db: Session, model: type[Any]) -> int:
    return int(db.execute(sa.select(sa.func.count()).select_from(model)).scalar_one())


def _build_dataset_summary(db: Session) -> dict[str, int]:
    return {
        "source_files_count": _count_rows(db, SourceFile),
        "raw_licitaciones_count": _count_rows(db, RawLicitacion),
        "raw_ordenes_compra_count": _count_rows(db, RawOrdenCompra),
        "normalized_licitaciones_count": _count_rows(db, NormalizedLicitacion),
        "normalized_licitacion_items_count": _count_rows(db, NormalizedLicitacionItem),
        "normalized_ofertas_count": _count_rows(db, NormalizedOferta),
        "normalized_ordenes_compra_count": _count_rows(db, NormalizedOrdenCompra),
        "normalized_ordenes_compra_items_count": _count_rows(db, NormalizedOrdenCompraItem),
    }


def _safe_manual_upload_token(file_token: str) -> str:
    token = file_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Manual upload token is required")
    if not token.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Manual upload token is invalid")
    return token


def _manual_upload_response_limit(settings: Settings) -> dict[str, int | str]:
    return {
        "max_size_bytes": settings.manual_upload_max_bytes,
        "max_size_label": format_manual_upload_size_limit(settings.manual_upload_max_bytes),
    }


async def _extract_multipart_payload(request: Request) -> tuple[str, str, bytes, str | None]:
    content_type = request.headers.get("content-type") or ""
    if "multipart/form-data" not in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail="Manual CSV upload must use multipart/form-data",
        )

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Manual CSV upload body is empty")

    dataset_values: list[str] = []
    file_items: list[tuple[str, str, bytes, str | None]] = []
    message = cast(
        Any,
        BytesParser(policy=email_default_policy).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        ),
    )
    if not message.is_multipart():
        raise HTTPException(status_code=400, detail="Manual CSV upload part is malformed")

    for part in message.iter_parts():
        part = cast(Any, part)
        if part.get_content_disposition() != "form-data":
            continue

        field_name = part.get_param("name", header="content-disposition") or ""
        file_name = part.get_filename()
        payload = part.get_payload(decode=True)
        payload_bytes = payload if isinstance(payload, bytes) else b""
        if file_name:
            file_items.append(
                (
                    field_name,
                    file_name,
                    payload_bytes,
                    part.get_content_type() if part.get_content_type() else None,
                )
            )
            continue

        if field_name == DATASET_FIELD_NAME:
            charset = part.get_content_charset() or "utf-8"
            dataset_values.append(payload_bytes.decode(charset).strip())

    if len(dataset_values) != 1 or not dataset_values[0]:
        raise HTTPException(
            status_code=400,
            detail="Select licitacion or orden_compra before uploading",
        )
    if len(file_items) != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one CSV file must be uploaded",
        )

    _, original_filename, file_bytes, file_type = file_items[0]
    return dataset_values[0], original_filename, bytes(file_bytes), file_type


def _duplicate_source_file_payload(source_file: SourceFile | None) -> dict[str, Any] | None:
    if source_file is None:
        return None
    return {
        "id": str(source_file.id),
        "dataset_type": source_file.dataset_type,
        "file_name": source_file.file_name,
        "file_path": source_file.file_path,
        "file_hash_sha256": source_file.file_hash_sha256,
        "status": source_file.status,
        "registered_at": source_file.registered_at,
        "source_meta": source_file.source_meta,
    }


def _manual_upload_telemetry(
    raw_metrics: dict[str, int],
    normalized_metrics: dict[str, dict[str, int]],
) -> dict[str, Any]:
    normalized_inserted_rows = sum(
        metrics.get("inserted_delta_rows", 0)
        for entity_name, metrics in normalized_metrics.items()
        if not entity_name.startswith("silver_")
    )
    silver_inserted_rows = sum(
        metrics.get("inserted_delta_rows", 0)
        for entity_name, metrics in normalized_metrics.items()
        if entity_name.startswith("silver_")
    )
    return {
        "processed_rows": raw_metrics["processed_rows"],
        "accepted_rows": raw_metrics["accepted_rows"],
        "inserted_delta_rows": raw_metrics["inserted_delta_rows"],
        "duplicate_existing_rows": raw_metrics["existing_or_updated_rows"],
        "rejected_rows": raw_metrics["rejected_rows"],
        "normalized_rows": normalized_inserted_rows,
        "silver_rows": silver_inserted_rows,
        "normalized_inserted_delta_rows": normalized_inserted_rows,
        "silver_inserted_delta_rows": silver_inserted_rows,
        "raw_ingest": raw_metrics,
        "entity_metrics": normalized_metrics,
    }


def _manual_upload_telemetry_seed() -> dict[str, Any]:
    return {
        "processed_rows": 0,
        "accepted_rows": 0,
        "inserted_delta_rows": 0,
        "duplicate_existing_rows": 0,
        "rejected_rows": 0,
        "normalized_rows": 0,
        "silver_rows": 0,
        "normalized_inserted_delta_rows": 0,
        "silver_inserted_delta_rows": 0,
        "raw_ingest": {},
        "entity_metrics": {},
    }


def _manual_upload_progress_payload(
    *,
    phase: str,
    label: str,
    detail: str,
    percent: int,
    raw_processed_rows: int,
    raw_total_rows: int,
    normalized_processed_rows: int,
    normalized_total_rows: int,
    updated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "label": label,
        "detail": detail,
        "percent": max(0, min(100, int(percent))),
        "raw_processed_rows": max(0, int(raw_processed_rows)),
        "raw_total_rows": max(0, int(raw_total_rows)),
        "normalized_processed_rows": max(0, int(normalized_processed_rows)),
        "normalized_total_rows": max(0, int(normalized_total_rows)),
        "updated_at": updated_at or datetime.now(UTC).isoformat(),
    }


def _manual_upload_progress_seed(preflight: ManualCsvPreflight) -> dict[str, Any]:
    total_rows = max(0, preflight.row_count)
    return _manual_upload_progress_payload(
        phase="preparing",
        label="Preparando carga manual",
        detail=f"{total_rows:,} filas listas para validar y cargar.",
        percent=5,
        raw_processed_rows=0,
        raw_total_rows=total_rows,
        normalized_processed_rows=0,
        normalized_total_rows=total_rows,
    )


def _manual_upload_progress_from_state(
    *,
    run: PipelineRun,
    preflight: ManualCsvPreflight,
) -> dict[str, Any]:
    run_orm: Any = run
    run_config: dict[str, Any] = run_orm.config if isinstance(run_orm.config, dict) else {}
    manual_upload = cast(dict[str, Any], run_config.get("manual_upload") or {})
    progress = manual_upload.get("progress")
    total_rows = max(0, preflight.row_count)

    if run_orm.status == "completed":
        telemetry = cast(dict[str, Any], run_config.get("telemetry") or {})
        processed_rows = int(telemetry.get("processed_rows") or total_rows)
        return _manual_upload_progress_payload(
            phase="completed",
            label="Carga completada",
            detail="Raw, Normalized y Silver cerrados.",
            percent=100,
            raw_processed_rows=processed_rows,
            raw_total_rows=max(total_rows, processed_rows),
            normalized_processed_rows=processed_rows,
            normalized_total_rows=max(total_rows, processed_rows),
            updated_at=str(
                (cast(dict[str, Any], progress).get("updated_at") if isinstance(progress, dict) else None)
                or (run_orm.finished_at.isoformat() if run_orm.finished_at else None)
                or datetime.now(UTC).isoformat()
            ),
        )

    if run_orm.status == "failed":
        detail = str(run_orm.error_summary or "Manual upload failed")
        return _manual_upload_progress_payload(
            phase="failed",
            label="Carga fallida",
            detail=detail,
            percent=100,
            raw_processed_rows=int(cast(dict[str, Any], progress).get("raw_processed_rows") or 0)
            if isinstance(progress, dict)
            else 0,
            raw_total_rows=int(cast(dict[str, Any], progress).get("raw_total_rows") or total_rows)
            if isinstance(progress, dict)
            else total_rows,
            normalized_processed_rows=int(
                cast(dict[str, Any], progress).get("normalized_processed_rows") or 0
            )
            if isinstance(progress, dict)
            else 0,
            normalized_total_rows=int(
                cast(dict[str, Any], progress).get("normalized_total_rows") or total_rows
            )
            if isinstance(progress, dict)
            else total_rows,
            updated_at=str(
                (cast(dict[str, Any], progress).get("updated_at") if isinstance(progress, dict) else None)
                or (run_orm.finished_at.isoformat() if run_orm.finished_at else None)
                or datetime.now(UTC).isoformat()
            ),
        )

    if isinstance(progress, dict) and progress:
        return _manual_upload_progress_payload(
            phase=str(progress.get("phase") or "preparing"),
            label=str(progress.get("label") or "Preparando carga manual"),
            detail=str(progress.get("detail") or "Backend listo para arrancar."),
            percent=int(progress.get("percent") or 0),
            raw_processed_rows=int(progress.get("raw_processed_rows") or 0),
            raw_total_rows=int(progress.get("raw_total_rows") or total_rows),
            normalized_processed_rows=int(progress.get("normalized_processed_rows") or 0),
            normalized_total_rows=int(progress.get("normalized_total_rows") or total_rows),
            updated_at=str(progress.get("updated_at") or datetime.now(UTC).isoformat()),
        )

    return _manual_upload_progress_seed(preflight)


def _set_manual_upload_progress(run: PipelineRun, progress: dict[str, Any]) -> None:
    run_orm: Any = run
    run_config: dict[str, Any] = run_orm.config if isinstance(run_orm.config, dict) else {}
    manual_upload = cast(dict[str, Any], run_config.get("manual_upload") or {})
    manual_upload["progress"] = progress
    run_config["manual_upload"] = manual_upload
    run_orm.config = run_config


def _persist_manual_upload_progress(job_id: UUID, progress: dict[str, Any]) -> None:
    with SessionLocal() as progress_db:
        run = progress_db.execute(
            sa.select(PipelineRun).where(PipelineRun.id == job_id)
        ).scalar_one_or_none()
        if run is None:
            return
        _set_manual_upload_progress(run, progress)
        progress_db.commit()


def _manual_upload_percent(base: int, span: int, processed: int, total: int | None) -> int:
    if total is None or total <= 0:
        return max(0, min(100, base))
    ratio = max(0.0, min(float(processed), float(total))) / float(total)
    return max(0, min(100, base + round(span * ratio)))


def _job_response(
    *,
    preflight: ManualCsvPreflight,
    source_file: SourceFile,
    run: PipelineRun,
    step: PipelineRunStep,
    batch: IngestionBatch,
) -> dict[str, Any]:
    run_orm: Any = run
    step_orm: Any = step
    batch_orm: Any = batch
    source_file_orm: Any = source_file
    run_config: dict[str, Any] = run_orm.config if isinstance(run_orm.config, dict) else {}
    telemetry = cast(dict[str, Any], run_config.get("telemetry") or _manual_upload_telemetry_seed())
    return {
        "job_id": str(run_orm.id),
        "status": run_orm.status,
        "terminal_state": run_orm.status in {"completed", "failed"},
        "progress": _manual_upload_progress_from_state(run=run, preflight=preflight),
        "step": {
            "name": step_orm.step_name,
            "status": step_orm.status,
            "rows_in": step_orm.rows_in,
            "rows_out": step_orm.rows_out,
            "rows_rejected": step_orm.rows_rejected,
            "error_details": step_orm.error_details,
        },
        "telemetry": telemetry,
        "source_file": _duplicate_source_file_payload(source_file_orm),
        "pipeline_run": {
            "id": str(run_orm.id),
            "run_key": run_orm.run_key,
            "dataset_type": run_orm.dataset_type,
            "status": run_orm.status,
            "started_at": run_orm.started_at,
            "finished_at": run_orm.finished_at,
            "error_summary": run_orm.error_summary,
            "config": run_config,
        },
        "ingestion_batch": {
            "id": str(batch_orm.id),
            "batch_key": batch_orm.batch_key,
            "status": batch_orm.status,
            "started_at": batch_orm.started_at,
            "finished_at": batch_orm.finished_at,
            "total_rows": batch_orm.total_rows,
            "loaded_rows": batch_orm.loaded_rows,
            "rejected_rows": batch_orm.rejected_rows,
        },
        "file_token": preflight.file_token,
        "dataset_type": preflight.dataset_type,
        "original_filename": preflight.original_filename,
        "canonical_filename": preflight.canonical_filename,
        "file_hash_sha256": preflight.file_hash_sha256,
        "row_count": preflight.row_count,
    }


def _register_source_file(
    db: Session,
    *,
    preflight: ManualCsvPreflight,
    process_started_at: datetime,
) -> tuple[SourceFile, bool]:
    existing = db.execute(
        sa.select(SourceFile).where(SourceFile.file_hash_sha256 == preflight.file_hash_sha256)
    ).scalar_one_or_none()
    if existing is not None:
        if existing.dataset_type != preflight.dataset_type:
            raise HTTPException(
                status_code=409,
                detail="Manual upload file hash is already registered for a different dataset",
            )
        source_file: Any = existing
        source_meta = dict(source_file.source_meta or {})
        source_meta["manual_upload"] = {
            **preflight.to_metadata_dict(),
            "process_started_at": process_started_at.isoformat(),
        }
        source_file.source_meta = source_meta
        return cast(SourceFile, source_file), False

    source_file = SourceFile(
        id=uuid4(),
        dataset_type=preflight.dataset_type,
        file_name=preflight.canonical_filename,
        file_path=preflight.staged_file_path,
        file_size_bytes=preflight.file_size_bytes,
        file_hash_sha256=preflight.file_hash_sha256,
        source_modified_at=None,
        status="registered",
        source_meta={
            "manual_upload": {
                **preflight.to_metadata_dict(),
                "process_started_at": process_started_at.isoformat(),
            }
        },
    )
    db.add(source_file)
    return cast(SourceFile, source_file), True


def _create_job_skeleton(
    *,
    source_file: SourceFile,
    preflight: ManualCsvPreflight,
    started_at: datetime,
) -> tuple[PipelineRun, PipelineRunStep, IngestionBatch]:
    run: Any = PipelineRun(
        id=uuid4(),
        run_key=f"manual-upload:{preflight.dataset_type}:{preflight.file_token}",
        dataset_type=preflight.dataset_type,
        source_file_id=source_file.id,
        status="running",
        started_at=started_at,
        config={
            "mode": "manual_csv_registration",
            "file_token": preflight.file_token,
            "file_hash_sha256": preflight.file_hash_sha256,
            "original_filename": preflight.original_filename,
            "canonical_filename": preflight.canonical_filename,
            "row_count": preflight.row_count,
            "preflight": preflight.to_metadata_dict(),
        },
    )
    step: Any = PipelineRunStep(
        id=uuid4(),
        run_id=run.id,
        step_name=MANUAL_UPLOAD_STEP_NAME,
        status="running",
        started_at=started_at,
    )
    batch: Any = IngestionBatch(
        id=uuid4(),
        source_file_id=source_file.id,
        batch_key=f"manual-upload:{preflight.file_token}",
        status="started",
        started_at=started_at,
    )
    return cast(PipelineRun, run), cast(PipelineRunStep, step), cast(IngestionBatch, batch)


def _finalize_job_records(
    *,
    source_file: SourceFile,
    preflight: ManualCsvPreflight,
    run: PipelineRun,
    step: PipelineRunStep,
    batch: IngestionBatch,
    completed_at: datetime,
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    source_file_orm: Any = source_file
    run_orm: Any = run
    step_orm: Any = step
    batch_orm: Any = batch

    source_meta = dict(source_file_orm.source_meta or {})
    source_meta["manual_upload"] = {
        **preflight.to_metadata_dict(),
        "processed_at": completed_at.isoformat(),
        "telemetry": telemetry,
    }
    source_file_orm.source_meta = source_meta

    run_orm.config = {
        **(run_orm.config or {}),
        "telemetry": telemetry,
        "completed_at": completed_at.isoformat(),
    }
    run_orm.status = "completed"
    run_orm.finished_at = completed_at

    step_orm.status = "completed"
    step_orm.finished_at = completed_at
    step_orm.rows_in = int(telemetry.get("processed_rows") or 0)
    step_orm.rows_out = int(telemetry.get("inserted_delta_rows") or 0)
    step_orm.rows_rejected = int(telemetry.get("rejected_rows") or 0)
    step_orm.error_details = {}

    batch_orm.status = "completed"
    batch_orm.finished_at = completed_at
    batch_orm.total_rows = int(telemetry.get("processed_rows") or 0)
    batch_orm.loaded_rows = int(telemetry.get("inserted_delta_rows") or 0)
    batch_orm.rejected_rows = int(telemetry.get("duplicate_existing_rows") or 0) + int(
        telemetry.get("rejected_rows") or 0
    )

    source_file_orm.status = "completed"

    return telemetry


def _run_manual_upload_pipeline(
    *,
    db: Session,
    preflight: ManualCsvPreflight,
    source_file: SourceFile,
    batch: IngestionBatch,
    run: PipelineRun,
    step: PipelineRunStep,
    on_raw_progress: Callable[[int, int | None], None] | None = None,
    on_normalized_progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    source_file_orm: Any = source_file
    batch_orm: Any = batch
    run_orm: Any = run
    step_orm: Any = step
    raw_metrics = process_registered_file(
        session=db,
        dataset_type=preflight.dataset_type,
        path=Path(preflight.staged_file_path),
        source_file=source_file_orm,
        batch=batch_orm,
        run=run_orm,
        step=step_orm,
        chunk_size=5_000,
        show_progress=False,
        precount=False,
        expected_rows=preflight.row_count,
        on_progress=on_raw_progress,
    )

    if preflight.dataset_type == "licitacion":
        normalized_result = process_licitaciones(
            session=db,
            fetch_size=10_000,
            chunk_size=500,
            limit_rows=0,
            show_progress=False,
            start_after_id=0,
            source_file_id=source_file_orm.id,
            debug_telemetry=False,
            state_checkpoint_every_pages=1,
            on_checkpoint=None,
            on_quality_checkpoint=None,
            on_progress=on_normalized_progress,
        )
    else:
        normalized_result = process_ordenes_compra(
            session=db,
            fetch_size=10_000,
            chunk_size=500,
            limit_rows=0,
            show_progress=False,
            start_after_id=0,
            source_file_id=source_file_orm.id,
            debug_telemetry=False,
            state_checkpoint_every_pages=1,
            on_checkpoint=None,
            on_quality_checkpoint=None,
            on_progress=on_normalized_progress,
        )

    return _manual_upload_telemetry(
        raw_metrics,
        cast(dict[str, dict[str, int]], normalized_result.get("entity_metrics") or {}),
    )


def _run_manual_upload_pipeline_background(
    *,
    job_id: UUID,
    preflight: ManualCsvPreflight,
) -> None:
    with SessionLocal() as job_db:
        run: Any = job_db.execute(sa.select(PipelineRun).where(PipelineRun.id == job_id)).scalar_one_or_none()
        if run is None:
            return

        step: Any = job_db.execute(
            sa.select(PipelineRunStep)
            .where(PipelineRunStep.run_id == job_id)
            .order_by(PipelineRunStep.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        source_file: Any = job_db.execute(
            sa.select(SourceFile).where(SourceFile.id == run.source_file_id)
        ).scalar_one_or_none()
        batch: Any = job_db.execute(
            sa.select(IngestionBatch)
            .where(IngestionBatch.source_file_id == run.source_file_id)
            .order_by(IngestionBatch.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if step is None or source_file is None or batch is None:
            return

        source_file_is_new = source_file.status == "registered"
        raw_total_rows = max(0, preflight.row_count)
        normalized_total_rows = max(0, preflight.row_count)

        def report_raw_progress(processed: int, total: int | None) -> None:
            total_rows = max(0, total or raw_total_rows)
            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="raw_ingest",
                    label="Registrando Raw",
                    detail=f"{processed:,}/{total_rows:,} filas leidas.",
                    percent=_manual_upload_percent(5, 40, processed, total_rows),
                    raw_processed_rows=processed,
                    raw_total_rows=total_rows,
                    normalized_processed_rows=0,
                    normalized_total_rows=normalized_total_rows,
                ),
            )

        def report_normalized_progress(processed: int, total: int) -> None:
            total_rows = max(0, total or normalized_total_rows)
            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="normalized",
                    label="Construyendo Normalized",
                    detail=f"{processed:,}/{total_rows:,} filas canonicas.",
                    percent=_manual_upload_percent(50, 45, processed, total_rows),
                    raw_processed_rows=raw_total_rows,
                    raw_total_rows=raw_total_rows,
                    normalized_processed_rows=processed,
                    normalized_total_rows=total_rows,
                ),
            )

        try:
            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="raw_ingest",
                    label="Arrancando carga",
                    detail=f"CSV listo. {raw_total_rows:,} filas para registrar en Raw.",
                    percent=10,
                    raw_processed_rows=0,
                    raw_total_rows=raw_total_rows,
                    normalized_processed_rows=0,
                    normalized_total_rows=normalized_total_rows,
                ),
            )
            raw_metrics = process_registered_file(
                session=job_db,
                dataset_type=preflight.dataset_type,
                path=Path(preflight.staged_file_path),
                source_file=source_file,
                batch=batch,
                run=run,
                step=step,
                chunk_size=5_000,
                show_progress=False,
                precount=False,
                expected_rows=preflight.row_count,
                on_progress=report_raw_progress,
            )

            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="normalized",
                    label="Construyendo capas canonicas",
                    detail="Raw listo. Normalized y Silver en marcha.",
                    percent=55,
                    raw_processed_rows=raw_metrics["processed_rows"],
                    raw_total_rows=raw_total_rows,
                    normalized_processed_rows=0,
                    normalized_total_rows=normalized_total_rows,
                ),
            )

            if preflight.dataset_type == "licitacion":
                normalized_result = process_licitaciones(
                    session=job_db,
                    fetch_size=10_000,
                    chunk_size=500,
                    limit_rows=0,
                    show_progress=False,
                    start_after_id=0,
                    source_file_id=source_file.id,
                    debug_telemetry=False,
                    state_checkpoint_every_pages=1,
                    on_checkpoint=None,
                    on_quality_checkpoint=None,
                    on_progress=report_normalized_progress,
                )
            else:
                normalized_result = process_ordenes_compra(
                    session=job_db,
                    fetch_size=10_000,
                    chunk_size=500,
                    limit_rows=0,
                    show_progress=False,
                    start_after_id=0,
                    source_file_id=source_file.id,
                    debug_telemetry=False,
                    state_checkpoint_every_pages=1,
                    on_checkpoint=None,
                    on_quality_checkpoint=None,
                    on_progress=report_normalized_progress,
                )

            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="finalizing",
                    label="Finalizando carga",
                    detail="Escribiendo telemetria y estado final.",
                    percent=98,
                    raw_processed_rows=raw_metrics["processed_rows"],
                    raw_total_rows=raw_total_rows,
                    normalized_processed_rows=int(
                        normalized_result.get("processed_rows") or normalized_total_rows
                    ),
                    normalized_total_rows=normalized_total_rows,
                ),
            )

            telemetry = _manual_upload_telemetry(
                raw_metrics,
                cast(dict[str, dict[str, int]], normalized_result.get("entity_metrics") or {}),
            )
            job_db.refresh(run)
            _finalize_job_records(
                source_file=source_file,
                preflight=preflight,
                run=run,
                step=step,
                batch=batch,
                completed_at=datetime.now(UTC),
                telemetry=telemetry,
            )
            job_db.commit()
            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="completed",
                    label="Carga completada",
                    detail="Raw, Normalized y Silver cerrados.",
                    percent=100,
                    raw_processed_rows=raw_metrics["processed_rows"],
                    raw_total_rows=raw_total_rows,
                    normalized_processed_rows=int(
                        normalized_result.get("processed_rows") or normalized_total_rows
                    ),
                    normalized_total_rows=normalized_total_rows,
                ),
            )
        except ManualUploadError as exc:
            job_db.rollback()
            _mark_job_failed(
                source_file=source_file,
                source_file_is_new=source_file_is_new,
                run=run,
                step=step,
                batch=batch,
                error_summary=str(exc),
            )
            job_db.commit()
            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="failed",
                    label="Carga fallida",
                    detail=str(exc),
                    percent=100,
                    raw_processed_rows=0,
                    raw_total_rows=raw_total_rows,
                    normalized_processed_rows=0,
                    normalized_total_rows=normalized_total_rows,
                ),
            )
        except Exception:  # noqa: BLE001
            job_db.rollback()
            safe_message = "Manual upload processing failed"
            _mark_job_failed(
                source_file=source_file,
                source_file_is_new=source_file_is_new,
                run=run,
                step=step,
                batch=batch,
                error_summary=safe_message,
            )
            job_db.commit()
            _persist_manual_upload_progress(
                job_id,
                _manual_upload_progress_payload(
                    phase="failed",
                    label="Carga fallida",
                    detail=safe_message,
                    percent=100,
                    raw_processed_rows=0,
                    raw_total_rows=raw_total_rows,
                    normalized_processed_rows=0,
                    normalized_total_rows=normalized_total_rows,
                ),
            )


def _mark_job_failed(
    *,
    source_file: SourceFile,
    source_file_is_new: bool,
    run: PipelineRun,
    step: PipelineRunStep,
    batch: IngestionBatch,
    error_summary: str,
) -> None:
    source_file_orm: Any = source_file
    run_orm: Any = run
    step_orm: Any = step
    batch_orm: Any = batch

    if source_file_is_new:
        source_file_orm.status = "failed"
        source_meta = dict(source_file_orm.source_meta or {})
        source_meta["manual_upload"] = {
            **(source_meta.get("manual_upload") or {}),
            "status": "failed",
            "error": error_summary,
        }
        source_file_orm.source_meta = source_meta

    run_orm.status = "failed"
    run_orm.error_summary = error_summary
    run_orm.finished_at = datetime.now(UTC)

    step_orm.status = "failed"
    step_orm.finished_at = datetime.now(UTC)
    step_orm.error_details = {"error": error_summary}

    batch_orm.status = "failed"
    batch_orm.finished_at = datetime.now(UTC)


def _manual_upload_error_status(exc: ManualUploadError) -> int:
    message = str(exc).lower()
    if "not found" in message or "invalid manual upload token" in message:
        return 404
    if "already consumed" in message or "different dataset" in message:
        return 409
    return 400


@router.post("/preflight")
async def preflight_manual_csv(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    try:
        dataset_type, original_filename, file_bytes, file_type = await _extract_multipart_payload(
            request
        )
        preflight = build_manual_csv_preflight(
            dataset_type=dataset_type,
            original_filename=original_filename,
            payload=file_bytes,
            intake_root=settings.manual_upload_root,
            max_bytes=settings.manual_upload_max_bytes,
            content_type=file_type,
        )
    except ManualUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        duplicate_source_file = db.execute(
            sa.select(SourceFile).where(SourceFile.file_hash_sha256 == preflight.file_hash_sha256)
        ).scalar_one_or_none()
        dataset_summary = _build_dataset_summary(db)
    except Exception:
        staged_dir = Path(preflight.staged_file_path).parent
        shutil.rmtree(staged_dir, ignore_errors=True)
        raise

    response = preflight.to_response_dict()
    response["duplicate_source_file"] = _duplicate_source_file_payload(
        duplicate_source_file
    )
    response["dataset_summary"] = dataset_summary
    response["upload_limits"] = _manual_upload_response_limit(settings)
    return response


@router.post("/{file_token}/process")
def process_manual_csv(
    file_token: str,
    background_tasks: BackgroundTasks = DEFAULT_BACKGROUND_TASKS,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    token = _safe_manual_upload_token(file_token)
    try:
        preflight = load_manual_upload_preflight(settings.manual_upload_root, token)
    except ManualUploadError as exc:
        raise HTTPException(status_code=_manual_upload_error_status(exc), detail=str(exc)) from exc

    if preflight.consumed_at is not None:
        raise HTTPException(status_code=409, detail="Manual upload token already consumed")

    started_at = datetime.now(UTC)
    source_file, source_file_is_new = _register_source_file(
        db,
        preflight=preflight,
        process_started_at=started_at,
    )
    db.flush()
    run, step, batch = _create_job_skeleton(
        source_file=source_file,
        preflight=preflight,
        started_at=started_at,
    )
    run_orm: Any = run
    db.add(run)
    db.add(step)
    db.add(batch)
    db.commit()

    try:
        consumed_preflight = mark_manual_upload_preflight_consumed(
            settings.manual_upload_root,
            preflight.file_token,
            str(run.id),
        )
        _set_manual_upload_progress(run, _manual_upload_progress_seed(consumed_preflight))
        db.commit()
        if background_tasks is DEFAULT_BACKGROUND_TASKS:
            telemetry = _run_manual_upload_pipeline(
                db=db,
                preflight=consumed_preflight,
                source_file=source_file,
                batch=batch,
                run=run,
                step=step,
                on_raw_progress=None,
                on_normalized_progress=None,
            )
            _finalize_job_records(
                source_file=source_file,
                preflight=consumed_preflight,
                run=run,
                step=step,
                batch=batch,
                completed_at=datetime.now(UTC),
                telemetry=telemetry,
            )
        else:
            background_tasks.add_task(
                _run_manual_upload_pipeline_background,
                job_id=cast(UUID, run_orm.id),
                preflight=consumed_preflight,
            )
        response = _job_response(
            preflight=consumed_preflight,
            source_file=source_file,
            run=run,
            step=step,
            batch=batch,
        )
        return response
    except ManualUploadError as exc:
        db.rollback()
        _mark_job_failed(
            source_file=source_file,
            source_file_is_new=source_file_is_new,
            run=run,
            step=step,
            batch=batch,
            error_summary=str(exc),
        )
        db.commit()
        raise HTTPException(
            status_code=_manual_upload_error_status(exc),
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        safe_message = "Manual upload processing failed"
        _mark_job_failed(
            source_file=source_file,
            source_file_is_new=source_file_is_new,
            run=run,
            step=step,
            batch=batch,
            error_summary=safe_message,
        )
        db.commit()
        raise HTTPException(status_code=500, detail=safe_message) from exc


@router.get("/jobs/{job_id}")
def get_manual_csv_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run: Any = db.execute(sa.select(PipelineRun).where(PipelineRun.id == job_id)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="manual upload job not found")

    step: Any = db.execute(
        sa.select(PipelineRunStep)
        .where(PipelineRunStep.run_id == job_id)
        .order_by(PipelineRunStep.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if step is None:
        raise HTTPException(status_code=404, detail="manual upload step not found")

    source_file: Any = db.execute(
        sa.select(SourceFile).where(SourceFile.id == run.source_file_id)
    ).scalar_one_or_none()
    if source_file is None:
        raise HTTPException(status_code=404, detail="manual upload source file not found")

    batch: Any = db.execute(
        sa.select(IngestionBatch)
        .where(IngestionBatch.source_file_id == source_file.id)
        .order_by(IngestionBatch.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="manual upload batch not found")

    run_orm: Any = run
    step_orm: Any = step
    source_file_orm: Any = source_file
    batch_orm: Any = batch
    run_config: dict[str, Any] = run_orm.config if isinstance(run_orm.config, dict) else {}
    telemetry = cast(dict[str, Any], run_config.get("telemetry") or {})
    response = _job_response(
        preflight=ManualCsvPreflight(
            file_token=str(run_config.get("file_token") or ""),
            dataset_type=str(run_orm.dataset_type),
            original_filename=str(run_config.get("original_filename") or ""),
            canonical_filename=str(run_config.get("canonical_filename") or ""),
            file_size_bytes=int(source_file_orm.file_size_bytes or 0),
            file_hash_sha256=str(run_config.get("file_hash_sha256") or ""),
            row_count=int(step_orm.rows_in or 0),
            missing_required_columns=tuple(),
            content_type=None,
            staged_file_path=str(source_file_orm.file_path),
            metadata_path="",
            staged_at=run_orm.started_at or datetime.now(UTC),
            consumed_at=run_orm.finished_at,
            consumed_job_id=str(run_orm.id),
        ),
        source_file=cast(SourceFile, source_file_orm),
        run=cast(PipelineRun, run_orm),
        step=cast(PipelineRunStep, step_orm),
        batch=cast(IngestionBatch, batch_orm),
    )
    response["telemetry"] = telemetry
    response["terminal_state"] = run_orm.status in {"completed", "failed"}
    return response
