from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, cast

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.api.dataset_summary import compute_dataset_summary_counts
from backend.models.operational import DatasetSummarySnapshot

SUMMARY_STRATEGY = "persisted_success_snapshot"
SUMMARY_PRECOMPUTED_STORAGE_STATUS = "enabled"
SUMMARY_SNAPSHOT_UNAVAILABLE_DETAIL = (
    "datasets summary snapshot unavailable and bootstrap refresh failed"
)
SUMMARY_REFRESH_FAILED_NO_FALLBACK_DETAIL = (
    "datasets summary refresh failed and no successful snapshot is available"
)
SUMMARY_AUTO_REFRESHED_STATUS = "auto_refreshed"
SUMMARY_AUTO_REFRESH_FAILED_STATUS = "auto_refresh_failed_using_last_successful_snapshot"


def latest_successful_snapshot(db: Session) -> DatasetSummarySnapshot | None:
    return db.execute(
        sa.select(DatasetSummarySnapshot)
        .where(DatasetSummarySnapshot.status == "success")
        .order_by(DatasetSummarySnapshot.generated_at.desc(), DatasetSummarySnapshot.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def persist_summary_snapshot(db: Session, *, refresh_mode: str) -> DatasetSummarySnapshot:
    counts = compute_dataset_summary_counts(db)
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


def build_snapshot_response(
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


def is_snapshot_from_today(snapshot: DatasetSummarySnapshot) -> bool:
    now_local_date = datetime.now(UTC).astimezone().date()
    snapshot_generated_at = cast(datetime, snapshot.generated_at)
    snapshot_local_date = snapshot_generated_at.astimezone().date()
    return snapshot_local_date == now_local_date


def read_datasets_summary(
    *,
    db: Session,
    mode: Literal["cached", "fresh"],
    max_age_seconds: int,
) -> dict[str, Any]:
    latest_snapshot = latest_successful_snapshot(db)

    if mode == "cached":
        if latest_snapshot is None:
            try:
                latest_snapshot = persist_summary_snapshot(db, refresh_mode="bootstrap")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                raise HTTPException(
                    status_code=503,
                    detail=SUMMARY_SNAPSHOT_UNAVAILABLE_DETAIL,
                ) from exc
        elif not is_snapshot_from_today(latest_snapshot):
            try:
                latest_snapshot = persist_summary_snapshot(db, refresh_mode="auto_daily")
                return build_snapshot_response(
                    latest_snapshot,
                    mode=mode,
                    max_age_seconds=max_age_seconds,
                    refresh_status=SUMMARY_AUTO_REFRESHED_STATUS,
                )
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                return build_snapshot_response(
                    latest_snapshot,
                    mode=mode,
                    max_age_seconds=max_age_seconds,
                    refresh_status=SUMMARY_AUTO_REFRESH_FAILED_STATUS,
                    refresh_error=type(exc).__name__,
                )

        return build_snapshot_response(
            latest_snapshot,
            mode=mode,
            max_age_seconds=max_age_seconds,
            refresh_status="not_requested",
        )

    try:
        fresh_snapshot = persist_summary_snapshot(db, refresh_mode="fresh")
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        fallback_snapshot = latest_successful_snapshot(db)
        if fallback_snapshot is None:
            raise HTTPException(
                status_code=503,
                detail=SUMMARY_REFRESH_FAILED_NO_FALLBACK_DETAIL,
            ) from exc

        return build_snapshot_response(
            fallback_snapshot,
            mode=mode,
            max_age_seconds=max_age_seconds,
            refresh_status="failed_using_last_successful_snapshot",
            refresh_error=type(exc).__name__,
        )

    return build_snapshot_response(
        fresh_snapshot,
        mode=mode,
        max_age_seconds=max_age_seconds,
        refresh_status="refreshed",
    )
