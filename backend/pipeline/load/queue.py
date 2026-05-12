from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

CLAIM_ORDER_FIELDS = ("priority", "available_at", "created_at", "id")

CLAIM_NEXT_JOB_SQL = sa.text(
    """
WITH next_job AS (
    SELECT id
    FROM pipeline_jobs
    WHERE status = 'queued'
      AND available_at <= :claim_time
    ORDER BY priority ASC, available_at ASC, created_at ASC, id ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE pipeline_jobs AS j
SET
    status = 'running',
    locked_at = :claim_time,
    locked_by = :worker_id,
    started_at = COALESCE(j.started_at, :claim_time),
    attempts = j.attempts + 1,
    updated_at = :claim_time
FROM next_job
WHERE j.id = next_job.id
RETURNING j.*;
"""
)

PROMOTE_RETRY_SCHEDULED_SQL = sa.text(
    """
UPDATE pipeline_jobs
SET
    status = 'queued',
    updated_at = :claim_time
WHERE status = 'retry_scheduled'
  AND available_at <= :claim_time
"""
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def compute_retry_available_at(
    *,
    failure_at: datetime,
    attempts: int,
    retry_delay_seconds: int,
) -> datetime:
    if attempts <= 0:
        raise ValueError("attempts must be >= 1")
    if retry_delay_seconds <= 0:
        raise ValueError("retry_delay_seconds must be > 0")
    return failure_at + timedelta(seconds=retry_delay_seconds * attempts)


def resolve_failure_state(
    *,
    attempts: int,
    max_attempts: int,
    failure_at: datetime,
    retry_delay_seconds: int,
    retryable: bool = True,
) -> tuple[str, datetime | None]:
    if max_attempts <= 0:
        raise ValueError("max_attempts must be > 0")
    if attempts <= 0:
        raise ValueError("attempts must be >= 1")
    if not retryable:
        return "dead_letter", None
    if attempts >= max_attempts:
        return "dead_letter", None
    return (
        "retry_scheduled",
        compute_retry_available_at(
            failure_at=failure_at,
            attempts=attempts,
            retry_delay_seconds=retry_delay_seconds,
        ),
    )


def promote_retry_scheduled_jobs(
    session: Session,
    *,
    claim_time: datetime,
) -> int:
    result = session.execute(PROMOTE_RETRY_SCHEDULED_SQL, {"claim_time": claim_time})
    return int(getattr(result, "rowcount", 0) or 0)


def claim_next_job(
    session: Session,
    *,
    worker_id: str,
    claim_time: datetime | None = None,
) -> dict[str, Any] | None:
    effective_claim_time = claim_time or _utc_now()
    promote_retry_scheduled_jobs(session, claim_time=effective_claim_time)
    result = session.execute(
        CLAIM_NEXT_JOB_SQL,
        {
            "claim_time": effective_claim_time,
            "worker_id": worker_id,
        },
    ).mappings()
    row = result.first()
    if row is None:
        return None
    return dict(row)


def fetch_source_checkpoint(
    session: Session,
    *,
    source_checkpoint_id: UUID,
) -> Mapping[str, Any]:
    row = (
        session.execute(
            sa.text(
                """
SELECT *
FROM source_checkpoints
WHERE id = :source_checkpoint_id
"""
            ),
            {"source_checkpoint_id": source_checkpoint_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise ValueError(f"source checkpoint not found: {source_checkpoint_id}")
    return cast(Mapping[str, Any], row)


def mark_job_completed(
    session: Session,
    *,
    job_id: UUID,
    finished_at: datetime | None = None,
) -> None:
    effective_time = finished_at or _utc_now()
    session.execute(
        sa.text(
            """
UPDATE pipeline_jobs
SET
    status = 'completed',
    finished_at = :finished_at,
    updated_at = :finished_at,
    locked_at = NULL,
    locked_by = NULL
WHERE id = :job_id
"""
        ),
        {"job_id": job_id, "finished_at": effective_time},
    )


def mark_job_failure(
    session: Session,
    *,
    job_id: UUID,
    error_message: str,
    retry_delay_seconds: int,
    max_attempts: int,
    retryable: bool,
    failure_at: datetime | None = None,
) -> str:
    effective_failure_at = failure_at or _utc_now()
    row = (
        session.execute(
            sa.text(
                """
SELECT attempts, max_attempts
FROM pipeline_jobs
WHERE id = :job_id
"""
            ),
            {"job_id": job_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise ValueError(f"job not found: {job_id}")
    row_mapping = cast(Mapping[str, Any], row)
    attempts = int(row_mapping["attempts"])
    row_max_attempts = row_mapping.get("max_attempts")
    effective_max_attempts = (
        int(row_max_attempts)
        if row_max_attempts is not None and int(row_max_attempts) > 0
        else max_attempts
    )
    next_state, available_at = resolve_failure_state(
        attempts=attempts,
        max_attempts=effective_max_attempts,
        failure_at=effective_failure_at,
        retry_delay_seconds=retry_delay_seconds,
        retryable=retryable,
    )
    session.execute(
        sa.text(
            """
UPDATE pipeline_jobs
SET
    status = :status,
    failed_at = :failure_at,
    error_message = :error_message,
    available_at = :available_at,
    updated_at = :failure_at,
    locked_at = NULL,
    locked_by = NULL
WHERE id = :job_id
"""
        ),
        {
            "job_id": job_id,
            "status": next_state,
            "failure_at": effective_failure_at,
            "error_message": error_message[:4000],
            "available_at": available_at,
        },
    )
    return next_state
