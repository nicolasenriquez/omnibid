from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.operational import SourceCheckpoint


def create_source_checkpoint(
    session: Session,
    *,
    source_kind: str,
    dataset_type: str,
    storage_uri: str,
    payload_hash_sha256: str,
    file_size_bytes: int,
    checkpoint_meta: Mapping[str, Any] | None = None,
    source_file_id: UUID | None = None,
) -> SourceCheckpoint:
    normalized_source_kind = source_kind.strip()
    normalized_dataset_type = dataset_type.strip()
    normalized_storage_uri = storage_uri.strip()
    normalized_hash = payload_hash_sha256.strip().lower()
    if normalized_source_kind == "":
        raise ValueError("source_kind is required")
    if normalized_dataset_type == "":
        raise ValueError("dataset_type is required")
    if normalized_storage_uri == "":
        raise ValueError("storage_uri is required")
    if len(normalized_hash) != 64:
        raise ValueError("payload_hash_sha256 must be a 64-char sha256 hex digest")
    if file_size_bytes < 0:
        raise ValueError("file_size_bytes must be >= 0")

    checkpoint = SourceCheckpoint(
        source_kind=normalized_source_kind,
        dataset_type=normalized_dataset_type,
        source_file_id=source_file_id,
        storage_uri=normalized_storage_uri,
        payload_hash_sha256=normalized_hash,
        file_size_bytes=file_size_bytes,
        checkpoint_meta=dict(checkpoint_meta or {}),
        status="staged",
    )
    session.add(checkpoint)
    session.flush()
    return checkpoint


def load_source_checkpoint(
    session: Session,
    *,
    checkpoint_id: UUID,
) -> SourceCheckpoint:
    checkpoint = session.get(SourceCheckpoint, checkpoint_id)
    if checkpoint is None:
        raise ValueError(f"source checkpoint not found: {checkpoint_id}")
    return checkpoint


def checkpoint_exists(checkpoint: SourceCheckpoint) -> bool:
    return Path(str(checkpoint.storage_uri)).exists()


def _set_model_attr(model: Any, name: str, value: Any) -> None:
    setattr(model, name, value)


def mark_source_checkpoint_consumed(
    session: Session,
    *,
    checkpoint_id: UUID,
    consumed_job_id: UUID,
    consumed_at: datetime | None = None,
) -> SourceCheckpoint:
    checkpoint = load_source_checkpoint(session, checkpoint_id=checkpoint_id)
    now = consumed_at or datetime.now(UTC)
    _set_model_attr(checkpoint, "status", "consumed")
    _set_model_attr(checkpoint, "consumed_at", now)
    _set_model_attr(checkpoint, "consumed_job_id", consumed_job_id)
    _set_model_attr(checkpoint, "updated_at", now)
    return checkpoint
