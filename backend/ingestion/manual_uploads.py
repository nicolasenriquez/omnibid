from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import secrets
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from backend.ingestion.contracts import validate_required_columns

MANUAL_UPLOAD_ALLOWED_DATASETS = {"licitacion", "orden_compra"}
MANUAL_UPLOAD_ALLOWED_CONTENT_TYPES = {
    "application/csv",
    "application/octet-stream",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
}
MANUAL_UPLOAD_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ManualUploadError(ValueError):
    pass


def _coerce_string_tuple(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        raise ManualUploadError("manual upload metadata is malformed")
    typed_values: list[Any] = values
    items: list[str] = []
    for value in typed_values:
        items.append(str(cast(Any, value)))
    return tuple(items)


@dataclass(frozen=True)
class ManualCsvPreflight:
    file_token: str
    dataset_type: str
    original_filename: str
    canonical_filename: str
    file_size_bytes: int
    file_hash_sha256: str
    row_count: int
    missing_required_columns: tuple[str, ...]
    content_type: str | None
    staged_file_path: str
    metadata_path: str
    staged_at: datetime
    consumed_at: datetime | None = None
    consumed_job_id: str | None = None

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "file_token": self.file_token,
            "dataset_type": self.dataset_type,
            "original_filename": self.original_filename,
            "canonical_filename": self.canonical_filename,
            "file_size_bytes": self.file_size_bytes,
            "file_hash_sha256": self.file_hash_sha256,
            "row_count": self.row_count,
            "missing_required_columns": list(self.missing_required_columns),
            "content_type": self.content_type,
            "staged_file_path": self.staged_file_path,
            "metadata_path": self.metadata_path,
            "staged_at": self.staged_at.isoformat(),
            "consumed_at": self.consumed_at.isoformat() if self.consumed_at else None,
            "consumed_job_id": self.consumed_job_id,
        }

    def to_response_dict(self) -> dict[str, Any]:
        payload = self.to_metadata_dict()
        payload["status"] = "consumed" if self.consumed_at else "staged"
        return payload

    @classmethod
    def from_metadata_dict(cls, metadata: dict[str, Any]) -> "ManualCsvPreflight":
        staged_at_raw = metadata.get("staged_at")
        consumed_at_raw = metadata.get("consumed_at")
        if not isinstance(staged_at_raw, str) or not staged_at_raw:
            raise ManualUploadError("manual upload metadata is missing staged_at")
        staged_at = datetime.fromisoformat(staged_at_raw)
        consumed_at = datetime.fromisoformat(consumed_at_raw) if consumed_at_raw else None
        missing_required_columns_raw_any: Any = metadata.get("missing_required_columns", [])
        return cls(
            file_token=str(metadata.get("file_token") or ""),
            dataset_type=str(metadata.get("dataset_type") or ""),
            original_filename=str(metadata.get("original_filename") or ""),
            canonical_filename=str(metadata.get("canonical_filename") or ""),
            file_size_bytes=int(str(metadata.get("file_size_bytes") or 0)),
            file_hash_sha256=str(metadata.get("file_hash_sha256") or ""),
            row_count=int(str(metadata.get("row_count") or 0)),
            missing_required_columns=_coerce_string_tuple(missing_required_columns_raw_any),
            content_type=(str(metadata.get("content_type")) if metadata.get("content_type") else None),
            staged_file_path=str(metadata.get("staged_file_path") or ""),
            metadata_path=str(metadata.get("metadata_path") or ""),
            staged_at=staged_at,
            consumed_at=consumed_at,
            consumed_job_id=(str(metadata.get("consumed_job_id")) if metadata.get("consumed_job_id") else None),
        )


def validate_manual_upload_dataset_type(dataset_type: str) -> str:
    normalized = dataset_type.strip().lower()
    if normalized not in MANUAL_UPLOAD_ALLOWED_DATASETS:
        allowed = ", ".join(sorted(MANUAL_UPLOAD_ALLOWED_DATASETS))
        raise ManualUploadError(f"dataset_type must be one of: {allowed}")
    return normalized


def validate_manual_upload_filename(original_filename: str) -> str:
    safe_name = original_filename.strip()
    if not safe_name:
        raise ManualUploadError("Uploaded filename is required")
    if Path(safe_name).name != safe_name or any(sep in safe_name for sep in ("/", "\\", ":")):
        raise ManualUploadError("Uploaded filename must not contain path components")
    if not safe_name.lower().endswith(".csv"):
        raise ManualUploadError("Uploaded file must have a .csv extension")
    return safe_name


def validate_manual_upload_content_type(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized == "":
        return None
    if normalized not in MANUAL_UPLOAD_ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(MANUAL_UPLOAD_ALLOWED_CONTENT_TYPES))
        raise ManualUploadError(f"Unsupported CSV content type: {normalized} (allowed: {allowed})")
    return normalized


def format_manual_upload_size_limit(max_bytes: int) -> str:
    if max_bytes < 0:
        raise ManualUploadError("manual upload max size must be non-negative")
    if max_bytes < 1024 * 1024:
        kibibytes = max_bytes / 1024 if max_bytes else 0
        if isinstance(kibibytes, float) and kibibytes.is_integer():
            return f"{int(kibibytes)} KiB"
        return f"{kibibytes:.1f} KiB"
    mebibytes = max_bytes / (1024 * 1024) if max_bytes else 0
    if isinstance(mebibytes, float) and mebibytes.is_integer():
        return f"{int(mebibytes)} MiB"
    return f"{mebibytes:.1f} MiB"


def _decode_manual_csv(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ManualUploadError("CSV encoding could not be decoded safely")


def _allocate_stage_directory(intake_root: Path) -> tuple[str, Path]:
    staging_root = intake_root / "staged"
    staging_root.mkdir(parents=True, exist_ok=True)
    for _ in range(64):
        file_token = secrets.token_urlsafe(16)
        if not MANUAL_UPLOAD_TOKEN_PATTERN.fullmatch(file_token):
            continue
        stage_dir = staging_root / file_token
        if stage_dir.exists():
            continue
        stage_dir.mkdir(parents=False, exist_ok=False)
        return file_token, stage_dir
    raise ManualUploadError("Unable to allocate a manual upload token")


def build_manual_csv_preflight(
    *,
    dataset_type: str,
    original_filename: str,
    payload: bytes,
    intake_root: Path,
    max_bytes: int,
    content_type: str | None = None,
) -> ManualCsvPreflight:
    normalized_dataset = validate_manual_upload_dataset_type(dataset_type)
    safe_original_filename = validate_manual_upload_filename(original_filename)
    normalized_content_type = validate_manual_upload_content_type(content_type)
    if max_bytes < 0:
        raise ManualUploadError("manual upload max size must be non-negative")
    if not payload:
        raise ManualUploadError("Uploaded CSV is empty")
    if len(payload) > max_bytes:
        limit_label = format_manual_upload_size_limit(max_bytes)
        raise ManualUploadError(f"Uploaded file exceeds the manual upload limit of {limit_label}")

    decoded_payload = _decode_manual_csv(payload)
    if "\x00" in decoded_payload:
        raise ManualUploadError("CSV encoding or delimiter must be corrected")

    reader = csv.reader(io.StringIO(decoded_payload), delimiter=";", quotechar='"')
    header = next(reader, None)
    if header is None:
        raise ManualUploadError("CSV header could not be parsed")
    header = [column.strip() for column in header]
    if not any(header):
        raise ManualUploadError("CSV header is empty")

    validation = validate_required_columns(normalized_dataset, header)
    if not validation.ok:
        missing = ", ".join(validation.missing_required_columns)
        raise ManualUploadError(
            f"Missing required columns for dataset={normalized_dataset}: {missing}"
        )

    row_count = sum(1 for row in reader if any(cell.strip() for cell in row))
    if row_count <= 0:
        raise ManualUploadError("Uploaded CSV must contain at least one data row")

    file_hash_sha256 = hashlib.sha256(payload).hexdigest()
    file_token, stage_dir = _allocate_stage_directory(intake_root)
    canonical_filename = f"manual-{normalized_dataset}-{file_token[:12]}.csv"
    staged_file_path = stage_dir / canonical_filename
    metadata_path = stage_dir / "preflight.json"
    staged_at = datetime.now(UTC)

    try:
        staged_file_path.write_bytes(payload)
        preflight = ManualCsvPreflight(
            file_token=file_token,
            dataset_type=normalized_dataset,
            original_filename=safe_original_filename,
            canonical_filename=canonical_filename,
            file_size_bytes=len(payload),
            file_hash_sha256=file_hash_sha256,
            row_count=row_count,
            missing_required_columns=validation.missing_required_columns,
            content_type=normalized_content_type,
            staged_file_path=str(staged_file_path),
            metadata_path=str(metadata_path),
            staged_at=staged_at,
        )
        metadata_path.write_text(
            json.dumps(preflight.to_metadata_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return preflight
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def _manual_upload_stage_dir(intake_root: Path, file_token: str) -> Path:
    if not MANUAL_UPLOAD_TOKEN_PATTERN.fullmatch(file_token):
        raise ManualUploadError("Invalid manual upload token")
    return intake_root / "staged" / file_token


def load_manual_upload_preflight(intake_root: Path, file_token: str) -> ManualCsvPreflight:
    stage_dir = _manual_upload_stage_dir(intake_root, file_token)
    metadata_path = stage_dir / "preflight.json"
    if not metadata_path.exists():
        raise ManualUploadError("Manual upload token not found")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    preflight = ManualCsvPreflight.from_metadata_dict(metadata)
    if preflight.file_token != file_token:
        raise ManualUploadError("Manual upload token mismatch")
    return preflight


def mark_manual_upload_preflight_consumed(
    intake_root: Path,
    file_token: str,
    job_id: str,
) -> ManualCsvPreflight:
    preflight = load_manual_upload_preflight(intake_root, file_token)
    if preflight.consumed_at is not None:
        raise ManualUploadError("Manual upload token already consumed")

    updated = ManualCsvPreflight(
        file_token=preflight.file_token,
        dataset_type=preflight.dataset_type,
        original_filename=preflight.original_filename,
        canonical_filename=preflight.canonical_filename,
        file_size_bytes=preflight.file_size_bytes,
        file_hash_sha256=preflight.file_hash_sha256,
        row_count=preflight.row_count,
        missing_required_columns=preflight.missing_required_columns,
        content_type=preflight.content_type,
        staged_file_path=preflight.staged_file_path,
        metadata_path=preflight.metadata_path,
        staged_at=preflight.staged_at,
        consumed_at=datetime.now(UTC),
        consumed_job_id=job_id,
    )

    metadata_path = Path(updated.metadata_path)
    metadata_path.write_text(
        json.dumps(updated.to_metadata_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return updated
