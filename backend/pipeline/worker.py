from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.ingestion.checkpoints import mark_source_checkpoint_consumed
from backend.ingestion import queue
from backend.pipeline.ingestion_units import (
    create_ingestion_unit,
    mark_ingestion_unit_completed,
    mark_ingestion_unit_failed,
)

JobHandler = Callable[..., Mapping[str, Any] | None]


class RetryableJobError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkerRunResult:
    action: str
    job_id: UUID | None = None
    ingestion_unit_id: UUID | None = None
    job_status: str | None = None


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
