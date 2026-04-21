from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.models.raw import RawLicitacion, RawOrdenCompra
from backend.models.operational import PipelineRun, SourceFile
from backend.models.normalized import (
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedOrdenCompra,
    NormalizedOrdenCompraItem,
)

router = APIRouter(tags=["operations"])


@router.get("/runs")
def list_runs(limit: int = 50, db: Session = Depends(get_db)) -> list[dict]:
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
def list_files(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(sa.select(SourceFile).order_by(SourceFile.registered_at.desc()).limit(limit)).scalars()
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
def datasets_summary(db: Session = Depends(get_db)) -> dict:
    def _safe_count(model: type) -> int | None:
        try:
            return db.execute(sa.select(sa.func.count()).select_from(model)).scalar_one()
        except Exception:  # noqa: BLE001
            db.rollback()
            return None

    files = _safe_count(SourceFile)
    lic_rows = _safe_count(RawLicitacion)
    oc_rows = _safe_count(RawOrdenCompra)
    normalized_lic = _safe_count(NormalizedLicitacion)
    normalized_items = _safe_count(NormalizedLicitacionItem)
    normalized_ofertas = _safe_count(NormalizedOferta)
    normalized_oc = _safe_count(NormalizedOrdenCompra)
    normalized_oc_items = _safe_count(NormalizedOrdenCompraItem)

    return {
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
    }
