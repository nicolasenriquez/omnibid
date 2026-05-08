from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.ingestion_jobs import IngestionUnit


def _require_non_empty_text(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if text == "":
        raise ValueError(f"{field_name} is required")
    return text


def _dict_any(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _set_model_attr(model: Any, name: str, value: Any) -> None:
    setattr(model, name, value)


def build_ingestion_unit_payload(
    *,
    job: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    source_kind = _require_non_empty_text(job.get("source_kind"), field_name="source_kind")
    dataset_type = _require_non_empty_text(job.get("dataset_type"), field_name="dataset_type")
    payload = job.get("payload")
    payload_mapping = _dict_any(payload)
    return {
        "job_id": job.get("id"),
        "source_checkpoint_id": job.get("source_checkpoint_id"),
        "source_kind": source_kind,
        "dataset_type": dataset_type,
        "source_file_id": payload_mapping.get("source_file_id"),
        "api_call_id": payload_mapping.get("api_call_id"),
        "period_start": payload_mapping.get("period_start"),
        "period_end": payload_mapping.get("period_end"),
        "raw_min_id": payload_mapping.get("raw_min_id"),
        "raw_max_id": payload_mapping.get("raw_max_id"),
        "metadata": dict(metadata),
    }


def create_ingestion_unit(
    session: Session,
    *,
    job: Mapping[str, Any],
    source_file_id: Any | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> IngestionUnit:
    payload = build_ingestion_unit_payload(job=job, metadata=metadata or {})
    resolved_source_file_id = source_file_id
    if resolved_source_file_id is None:
        resolved_source_file_id = payload["source_file_id"]
    unit = IngestionUnit(
        job_id=payload["job_id"],
        source_checkpoint_id=payload["source_checkpoint_id"],
        source_kind=payload["source_kind"],
        dataset_type=payload["dataset_type"],
        source_file_id=resolved_source_file_id,
        api_call_id=payload["api_call_id"],
        period_start=payload["period_start"],
        period_end=payload["period_end"],
        raw_min_id=payload["raw_min_id"],
        raw_max_id=payload["raw_max_id"],
        status="started",
        metadata_json=payload["metadata"],
    )
    session.add(unit)
    session.flush()
    return unit


def mark_ingestion_unit_completed(
    session: Session,
    *,
    ingestion_unit_id: UUID,
    metadata_patch: Mapping[str, Any] | None = None,
    finished_at: datetime | None = None,
) -> None:
    unit = session.get(IngestionUnit, ingestion_unit_id)
    if unit is None:
        raise ValueError(f"ingestion unit not found: {ingestion_unit_id}")
    next_meta = _dict_any(unit.metadata_json)
    if metadata_patch:
        next_meta.update(dict(metadata_patch))
    completed_at = finished_at or datetime.now(UTC)
    _set_model_attr(unit, "metadata_json", next_meta)
    _set_model_attr(unit, "status", "completed")
    _set_model_attr(unit, "finished_at", completed_at)
    _set_model_attr(unit, "updated_at", completed_at)


def mark_ingestion_unit_failed(
    session: Session,
    *,
    ingestion_unit_id: UUID,
    error_message: str,
    failed_at: datetime | None = None,
) -> None:
    unit = session.get(IngestionUnit, ingestion_unit_id)
    if unit is None:
        raise ValueError(f"ingestion unit not found: {ingestion_unit_id}")
    when = failed_at or datetime.now(UTC)
    next_meta = _dict_any(unit.metadata_json)
    next_meta["error_message"] = error_message[:4000]
    _set_model_attr(unit, "metadata_json", next_meta)
    _set_model_attr(unit, "status", "failed")
    _set_model_attr(unit, "finished_at", when)
    _set_model_attr(unit, "updated_at", when)
