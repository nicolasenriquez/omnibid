from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.ingestion_jobs import IngestionUnit
from backend.pipeline.load.checkpoints import mark_source_checkpoint_consumed
from backend.pipeline.load import queue

JobHandler = Callable[..., Mapping[str, Any] | None]


class RetryableJobError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkerRunResult:
    action: str
    job_id: UUID | None = None
    ingestion_unit_id: UUID | None = None
    job_status: str | None = None


# ---------------------------------------------------------------------------
# Ingestion unit helpers (consolidated from ingestion_units.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Worker loop
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(UTC)


def _run_job_handler(
    *,
    handler: JobHandler,
    session: Session,
    job: Mapping[str, Any],
    ingestion_unit_id: UUID,
) -> Mapping[str, Any] | None:
    return handler(
        session=session,
        job=job,
        ingestion_unit_id=ingestion_unit_id,
    )


def run_worker_once(
    session: Session,
    *,
    worker_id: str,
    handlers: Mapping[str, JobHandler],
    retry_delay_seconds: int,
    max_attempts: int,
    claim_time: datetime | None = None,
) -> WorkerRunResult:
    now = claim_time or _utc_now()
    job = queue.claim_next_job(
        session,
        worker_id=worker_id,
        claim_time=now,
    )
    if job is None:
        return WorkerRunResult(action="idle")

    job_id = UUID(str(job["id"]))
    source_checkpoint = queue.fetch_source_checkpoint(
        session,
        source_checkpoint_id=UUID(str(job["source_checkpoint_id"])),
    )
    ingestion_unit = create_ingestion_unit(
        session,
        job=job,
        source_file_id=source_checkpoint.get("source_file_id"),
        metadata={"worker_id": worker_id},
    )
    ingestion_unit_id = UUID(str(ingestion_unit.id))

    handler = handlers.get(str(job["job_type"]))
    if handler is None:
        mark_ingestion_unit_failed(
            session,
            ingestion_unit_id=ingestion_unit_id,
            error_message=f"No handler registered for job_type={job['job_type']}",
            failed_at=now,
        )
        queue.mark_job_failure(
            session,
            job_id=job_id,
            error_message=f"No handler registered for job_type={job['job_type']}",
            retry_delay_seconds=retry_delay_seconds,
            max_attempts=max_attempts,
            retryable=False,
            failure_at=now,
        )
        return WorkerRunResult(
            action="failed",
            job_id=job_id,
            ingestion_unit_id=ingestion_unit_id,
            job_status="dead_letter",
        )

    try:
        outcome = _run_job_handler(
            handler=handler,
            session=session,
            job=job,
            ingestion_unit_id=ingestion_unit_id,
        ) or {}
        completed_at = _utc_now()
        mark_ingestion_unit_completed(
            session,
            ingestion_unit_id=ingestion_unit_id,
            metadata_patch=outcome,
            finished_at=completed_at,
        )
        mark_source_checkpoint_consumed(
            session,
            checkpoint_id=UUID(str(job["source_checkpoint_id"])),
            consumed_job_id=job_id,
            consumed_at=completed_at,
        )
        queue.mark_job_completed(
            session,
            job_id=job_id,
            finished_at=completed_at,
        )
        return WorkerRunResult(
            action="completed",
            job_id=job_id,
            ingestion_unit_id=ingestion_unit_id,
            job_status="completed",
        )
    except RetryableJobError as exc:
        failed_at = _utc_now()
        mark_ingestion_unit_failed(
            session,
            ingestion_unit_id=ingestion_unit_id,
            error_message=str(exc),
            failed_at=failed_at,
        )
        next_status = queue.mark_job_failure(
            session,
            job_id=job_id,
            error_message=str(exc),
            retry_delay_seconds=retry_delay_seconds,
            max_attempts=max_attempts,
            retryable=True,
            failure_at=failed_at,
        )
        return WorkerRunResult(
            action="failed",
            job_id=job_id,
            ingestion_unit_id=ingestion_unit_id,
            job_status=next_status,
        )
    except Exception as exc:  # pragma: no cover - defensive guard for operator loop
        failed_at = _utc_now()
        mark_ingestion_unit_failed(
            session,
            ingestion_unit_id=ingestion_unit_id,
            error_message=str(exc),
            failed_at=failed_at,
        )
        next_status = queue.mark_job_failure(
            session,
            job_id=job_id,
            error_message=str(exc),
            retry_delay_seconds=retry_delay_seconds,
            max_attempts=max_attempts,
            retryable=False,
            failure_at=failed_at,
        )
        return WorkerRunResult(
            action="failed",
            job_id=job_id,
            ingestion_unit_id=ingestion_unit_id,
            job_status=next_status,
        )
