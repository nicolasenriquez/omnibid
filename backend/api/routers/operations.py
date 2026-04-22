from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.models.normalized import (
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedOrdenCompra,
    NormalizedOrdenCompraItem,
)
from backend.models.operational import DatasetSummarySnapshot, PipelineRun, SourceFile
from backend.models.raw import RawLicitacion, RawOrdenCompra

router = APIRouter(tags=["operations"])

RUNS_LIMIT_DEFAULT = 50
RUNS_LIMIT_MAX = 200
FILES_LIMIT_DEFAULT = 100
FILES_LIMIT_MAX = 200
SUMMARY_CACHE_MAX_AGE_DEFAULT_SECONDS = 300
SUMMARY_CACHE_MAX_AGE_MIN_SECONDS = 10
SUMMARY_CACHE_MAX_AGE_MAX_SECONDS = 3_600
SUMMARY_STRATEGY = "persisted_success_snapshot"
SUMMARY_PRECOMPUTED_STORAGE_STATUS = "enabled"
SUMMARY_SNAPSHOT_UNAVAILABLE_DETAIL = (
    "datasets summary snapshot unavailable and bootstrap refresh failed"
)
SUMMARY_REFRESH_FAILED_NO_FALLBACK_DETAIL = (
    "datasets summary refresh failed and no successful snapshot is available"
)


def reset_datasets_summary_cache() -> None:
    # Backward-compatible no-op: summaries are persisted in operational storage.
    return None


def _count_rows(db: Session, model: type[Any]) -> int:
    return db.execute(sa.select(sa.func.count()).select_from(model)).scalar_one()


def _compute_summary_counts(db: Session) -> dict[str, int]:
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


def _latest_successful_snapshot(db: Session) -> DatasetSummarySnapshot | None:
    return db.execute(
        sa.select(DatasetSummarySnapshot)
        .where(DatasetSummarySnapshot.status == "success")
        .order_by(DatasetSummarySnapshot.generated_at.desc(), DatasetSummarySnapshot.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _persist_summary_snapshot(db: Session, *, refresh_mode: str) -> DatasetSummarySnapshot:
    counts = _compute_summary_counts(db)
    generated_at = datetime.now(UTC)
    snapshot = DatasetSummarySnapshot(
        generated_at=generated_at,
        refresh_mode=refresh_mode,
        status="success",
        error_details={},
        **counts,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _build_snapshot_response(
    snapshot: DatasetSummarySnapshot,
    *,
    mode: Literal["cached", "fresh"],
    max_age_seconds: int,
    refresh_status: str,
    refresh_error: str | None = None,
) -> dict[str, Any]:
    age_seconds = max(0, int((datetime.now(UTC) - snapshot.generated_at).total_seconds()))
    summary_meta: dict[str, Any] = {
        "mode": mode,
        "is_cached": False,
        "generated_at": snapshot.generated_at.isoformat(),
        "max_age_seconds": max_age_seconds,
        "strategy": SUMMARY_STRATEGY,
        "precomputed_summary_storage": SUMMARY_PRECOMPUTED_STORAGE_STATUS,
        "snapshot_id": str(snapshot.id),
        "snapshot_status": snapshot.status,
        "snapshot_refresh_mode": snapshot.refresh_mode,
        "snapshot_age_seconds": age_seconds,
        "is_stale": age_seconds > max_age_seconds,
        "refresh_status": refresh_status,
    }
    if refresh_error is not None:
        summary_meta["refresh_error"] = refresh_error

    return {
        "source_files": snapshot.source_files_count,
        "raw_rows": {
            "licitaciones": snapshot.raw_licitaciones_count,
            "ordenes_compra": snapshot.raw_ordenes_compra_count,
        },
        "normalized_rows": {
            "licitaciones": snapshot.normalized_licitaciones_count,
            "licitacion_items": snapshot.normalized_licitacion_items_count,
            "ofertas": snapshot.normalized_ofertas_count,
            "ordenes_compra": snapshot.normalized_ordenes_compra_count,
            "ordenes_compra_items": snapshot.normalized_ordenes_compra_items_count,
        },
        "summary_meta": summary_meta,
    }


@router.get("/runs")
def list_runs(
    limit: int = Query(default=RUNS_LIMIT_DEFAULT, ge=1, le=RUNS_LIMIT_MAX),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(
        sa.select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
    ).scalars()
    return [
        {
            "id": str(r.id),
            "run_key": r.run_key,
            "dataset_type": r.dataset_type,
            "status": r.status,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "source_file_id": str(r.source_file_id) if r.source_file_id else None,
        }
        for r in rows
    ]


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    run = db.execute(sa.select(PipelineRun).where(PipelineRun.id == run_id)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "id": str(run.id),
        "run_key": run.run_key,
        "dataset_type": run.dataset_type,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error_summary": run.error_summary,
        "source_file_id": str(run.source_file_id) if run.source_file_id else None,
    }


@router.get("/files")
def list_files(
    limit: int = Query(default=FILES_LIMIT_DEFAULT, ge=1, le=FILES_LIMIT_MAX),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(
        sa.select(SourceFile)
        .order_by(SourceFile.registered_at.desc())
        .limit(limit)
    ).scalars()
    return [
        {
            "id": str(f.id),
            "dataset_type": f.dataset_type,
            "file_name": f.file_name,
            "file_path": f.file_path,
            "file_hash_sha256": f.file_hash_sha256,
            "status": f.status,
            "registered_at": f.registered_at,
            "file_size_bytes": f.file_size_bytes,
        }
        for f in rows
    ]


@router.get("/files/{source_file_id}")
def get_file(source_file_id: str, db: Session = Depends(get_db)) -> dict:
    source = db.execute(sa.select(SourceFile).where(SourceFile.id == source_file_id)).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="source file not found")
    return {
        "id": str(source.id),
        "dataset_type": source.dataset_type,
        "file_name": source.file_name,
        "file_path": source.file_path,
        "file_hash_sha256": source.file_hash_sha256,
        "status": source.status,
        "registered_at": source.registered_at,
        "source_meta": source.source_meta,
    }


@router.get("/datasets/summary")
def datasets_summary(
    mode: Literal["cached", "fresh"] = Query(default="cached"),
    max_age_seconds: int = Query(
        default=SUMMARY_CACHE_MAX_AGE_DEFAULT_SECONDS,
        ge=SUMMARY_CACHE_MAX_AGE_MIN_SECONDS,
        le=SUMMARY_CACHE_MAX_AGE_MAX_SECONDS,
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    latest_snapshot = _latest_successful_snapshot(db)

    if mode == "cached":
        if latest_snapshot is None:
            try:
                latest_snapshot = _persist_summary_snapshot(db, refresh_mode="bootstrap")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                raise HTTPException(
                    status_code=503,
                    detail=SUMMARY_SNAPSHOT_UNAVAILABLE_DETAIL,
                ) from exc

        return _build_snapshot_response(
            latest_snapshot,
            mode=mode,
            max_age_seconds=max_age_seconds,
            refresh_status="not_requested",
        )

    try:
        fresh_snapshot = _persist_summary_snapshot(db, refresh_mode="fresh")
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        fallback_snapshot = _latest_successful_snapshot(db)
        if fallback_snapshot is None:
            raise HTTPException(
                status_code=503,
                detail=SUMMARY_REFRESH_FAILED_NO_FALLBACK_DETAIL,
            ) from exc

        return _build_snapshot_response(
            fallback_snapshot,
            mode=mode,
            max_age_seconds=max_age_seconds,
            refresh_status="failed_using_last_successful_snapshot",
            refresh_error=type(exc).__name__,
        )

    return _build_snapshot_response(
        fresh_snapshot,
        mode=mode,
        max_age_seconds=max_age_seconds,
        refresh_status="refreshed",
    )
