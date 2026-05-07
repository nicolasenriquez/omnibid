from __future__ import annotations

from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import sqlalchemy as sa

from backend.api.deps import get_db
from backend.api.services.dataset_summary_snapshots import (
    SUMMARY_AUTO_REFRESH_FAILED_STATUS,
    SUMMARY_AUTO_REFRESHED_STATUS,
    SUMMARY_PRECOMPUTED_STORAGE_STATUS,
    SUMMARY_REFRESH_FAILED_NO_FALLBACK_DETAIL,
    SUMMARY_SNAPSHOT_UNAVAILABLE_DETAIL,
    SUMMARY_STRATEGY,
    read_datasets_summary,
)
from backend.models.operational import PipelineRun, SourceFile

router = APIRouter(tags=["operations"])

RUNS_LIMIT_DEFAULT = 50
RUNS_LIMIT_MAX = 200
FILES_LIMIT_DEFAULT = 100
FILES_LIMIT_MAX = 200
SUMMARY_CACHE_MAX_AGE_DEFAULT_SECONDS = 300
SUMMARY_CACHE_MAX_AGE_MIN_SECONDS = 10
SUMMARY_CACHE_MAX_AGE_MAX_SECONDS = 3_600

__all__ = [
    "FILES_LIMIT_DEFAULT",
    "FILES_LIMIT_MAX",
    "RUNS_LIMIT_DEFAULT",
    "RUNS_LIMIT_MAX",
    "SUMMARY_AUTO_REFRESH_FAILED_STATUS",
    "SUMMARY_AUTO_REFRESHED_STATUS",
    "SUMMARY_CACHE_MAX_AGE_DEFAULT_SECONDS",
    "SUMMARY_CACHE_MAX_AGE_MAX_SECONDS",
    "SUMMARY_CACHE_MAX_AGE_MIN_SECONDS",
    "SUMMARY_PRECOMPUTED_STORAGE_STATUS",
    "SUMMARY_REFRESH_FAILED_NO_FALLBACK_DETAIL",
    "SUMMARY_SNAPSHOT_UNAVAILABLE_DETAIL",
    "SUMMARY_STRATEGY",
]


@router.get("/runs")
def list_runs(
    limit: int = Query(default=RUNS_LIMIT_DEFAULT, ge=1, le=RUNS_LIMIT_MAX),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.execute(
        sa.select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
    ).scalars()
    results: list[dict[str, Any]] = []
    for run in rows:
        source_file_id_value = cast(Any, run).source_file_id
        results.append(
            {
                "id": str(run.id),
                "run_key": run.run_key,
                "dataset_type": run.dataset_type,
                "status": run.status,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "source_file_id": (
                    str(source_file_id_value) if source_file_id_value is not None else None
                ),
            }
        )
    return results


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    run = db.execute(sa.select(PipelineRun).where(PipelineRun.id == run_id)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    source_file_id_value = cast(Any, run).source_file_id
    return {
        "id": str(run.id),
        "run_key": run.run_key,
        "dataset_type": run.dataset_type,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error_summary": run.error_summary,
        "source_file_id": str(source_file_id_value) if source_file_id_value is not None else None,
    }


@router.get("/files")
def list_files(
    limit: int = Query(default=FILES_LIMIT_DEFAULT, ge=1, le=FILES_LIMIT_MAX),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
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
def get_file(source_file_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
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
    return read_datasets_summary(
        db=db,
        mode=mode,
        max_age_seconds=max_age_seconds,
    )
