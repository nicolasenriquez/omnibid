from __future__ import annotations

import copy
from datetime import UTC, datetime
from threading import Lock
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
from backend.models.operational import PipelineRun, SourceFile
from backend.models.raw import RawLicitacion, RawOrdenCompra

router = APIRouter(tags=["operations"])

RUNS_LIMIT_DEFAULT = 50
RUNS_LIMIT_MAX = 200
FILES_LIMIT_DEFAULT = 100
FILES_LIMIT_MAX = 200
SUMMARY_CACHE_MAX_AGE_DEFAULT_SECONDS = 300
SUMMARY_CACHE_MAX_AGE_MIN_SECONDS = 10
SUMMARY_CACHE_MAX_AGE_MAX_SECONDS = 3_600
SUMMARY_STRATEGY = "ttl_cached_full_counts"
SUMMARY_PRECOMPUTED_STORAGE_STATUS = "deferred_followup_proposal_required"
_DATASETS_SUMMARY_CACHE_LOCK = Lock()
_DATASETS_SUMMARY_CACHE: dict[str, Any] = {}


def reset_datasets_summary_cache() -> None:
    with _DATASETS_SUMMARY_CACHE_LOCK:
        _DATASETS_SUMMARY_CACHE.clear()


def _safe_count(db: Session, model: type[Any]) -> int | None:
    try:
        return db.execute(sa.select(sa.func.count()).select_from(model)).scalar_one()
    except Exception:  # noqa: BLE001
        db.rollback()
        return None


def _build_summary_payload(db: Session) -> tuple[dict[str, Any], bool]:
    files = _safe_count(db, SourceFile)
    lic_rows = _safe_count(db, RawLicitacion)
    oc_rows = _safe_count(db, RawOrdenCompra)
    normalized_lic = _safe_count(db, NormalizedLicitacion)
    normalized_items = _safe_count(db, NormalizedLicitacionItem)
    normalized_ofertas = _safe_count(db, NormalizedOferta)
    normalized_oc = _safe_count(db, NormalizedOrdenCompra)
    normalized_oc_items = _safe_count(db, NormalizedOrdenCompraItem)
    counts: list[int | None] = [
        files,
        lic_rows,
        oc_rows,
        normalized_lic,
        normalized_items,
        normalized_ofertas,
        normalized_oc,
        normalized_oc_items,
    ]
    payload_is_complete = all(value is not None for value in counts)

    return (
        {
            "source_files": files,
            "raw_rows": {
                "licitaciones": lic_rows,
                "ordenes_compra": oc_rows,
            },
            "normalized_rows": {
                "licitaciones": normalized_lic,
                "licitacion_items": normalized_items,
                "ofertas": normalized_ofertas,
                "ordenes_compra": normalized_oc,
                "ordenes_compra_items": normalized_oc_items,
            },
        },
        payload_is_complete,
    )


def _read_cached_summary(max_age_seconds: int) -> tuple[dict[str, Any] | None, datetime | None]:
    with _DATASETS_SUMMARY_CACHE_LOCK:
        payload = _DATASETS_SUMMARY_CACHE.get("payload")
        generated_at = _DATASETS_SUMMARY_CACHE.get("generated_at")
        if not isinstance(payload, dict) or not isinstance(generated_at, datetime):
            return None, None
        cached_payload = copy.deepcopy(payload)

    age_seconds = (datetime.now(UTC) - generated_at).total_seconds()
    if age_seconds > max_age_seconds:
        return None, None
    return cached_payload, generated_at


def _write_cached_summary(payload: dict[str, Any]) -> datetime:
    generated_at = datetime.now(UTC)
    with _DATASETS_SUMMARY_CACHE_LOCK:
        _DATASETS_SUMMARY_CACHE["payload"] = copy.deepcopy(payload)
        _DATASETS_SUMMARY_CACHE["generated_at"] = generated_at
    return generated_at


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
    if mode == "cached":
        cached_payload, generated_at = _read_cached_summary(max_age_seconds)
        if cached_payload is not None and generated_at is not None:
            return {
                **cached_payload,
                "summary_meta": {
                    "mode": mode,
                    "is_cached": True,
                    "generated_at": generated_at.isoformat(),
                    "max_age_seconds": max_age_seconds,
                    "strategy": SUMMARY_STRATEGY,
                    "precomputed_summary_storage": SUMMARY_PRECOMPUTED_STORAGE_STATUS,
                },
            }

    payload, payload_is_complete = _build_summary_payload(db)
    if payload_is_complete:
        generated_at = _write_cached_summary(payload)
    else:
        generated_at = datetime.now(UTC)
    return {
        **payload,
        "summary_meta": {
            "mode": mode,
            "is_cached": False,
            "generated_at": generated_at.isoformat(),
            "max_age_seconds": max_age_seconds,
            "strategy": SUMMARY_STRATEGY,
            "precomputed_summary_storage": SUMMARY_PRECOMPUTED_STORAGE_STATUS,
        },
    }
