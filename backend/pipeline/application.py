from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.models.operational import IngestionBatch, PipelineRun, PipelineRunStep, SourceFile
from backend.ingestion.contracts import normalize_dataset_type

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_normalized import process_licitaciones, process_ordenes_compra  # noqa: E402
from scripts.ingest_raw import process_registered_file  # noqa: E402

RAW_CHUNK_SIZE = 5_000
NORMALIZED_FETCH_SIZE = 10_000
NORMALIZED_CHUNK_SIZE = 500
IMPLEMENTED_SOURCE_PROFILE = "csv_drop"
DOCUMENTED_SOURCE_PROFILES = ("csv_drop", "api_json", "open_data_snapshot")


def normalize_source_profile(source_profile: str) -> str:
    normalized = source_profile.strip().lower()
    if normalized != IMPLEMENTED_SOURCE_PROFILE:
        allowed_profiles = ", ".join(DOCUMENTED_SOURCE_PROFILES)
        raise ValueError(
            f"unsupported source profile: {normalized}. Supported profiles: {allowed_profiles}"
        )
    return normalized


def resolve_normalized_build_processor(dataset_type: str) -> Callable[..., dict[str, Any]]:
    normalized_dataset_type = normalize_dataset_type(dataset_type)
    if normalized_dataset_type == "licitacion":
        return process_licitaciones
    return process_ordenes_compra


def run_registered_raw_ingest(
    session: Session,
    *,
    dataset_type: str,
    source_profile: str = IMPLEMENTED_SOURCE_PROFILE,
    path: Path,
    source_file: SourceFile,
    batch: IngestionBatch,
    run: PipelineRun,
    step: PipelineRunStep,
    expected_rows: int | None = None,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> dict[str, int]:
    normalize_source_profile(source_profile)
    normalized_dataset_type = normalize_dataset_type(dataset_type)
    return process_registered_file(
        session=session,
        dataset_type=normalized_dataset_type,
        path=path,
        source_file=source_file,
        batch=batch,
        run=run,
        step=step,
        chunk_size=RAW_CHUNK_SIZE,
        show_progress=False,
        precount=False,
        expected_rows=expected_rows,
        on_progress=on_progress,
    )


def run_normalized_build(
    session: Session,
    *,
    dataset_type: str,
    source_profile: str = IMPLEMENTED_SOURCE_PROFILE,
    source_file_id: Any,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    normalize_source_profile(source_profile)
    processor = resolve_normalized_build_processor(dataset_type)
    base_kwargs: dict[str, Any] = {
        "session": session,
        "fetch_size": NORMALIZED_FETCH_SIZE,
        "chunk_size": NORMALIZED_CHUNK_SIZE,
        "limit_rows": 0,
        "show_progress": False,
        "start_after_id": 0,
        "source_file_id": source_file_id,
        "debug_telemetry": False,
        "state_checkpoint_every_pages": 1,
        "on_checkpoint": None,
        "on_quality_checkpoint": None,
        "on_progress": on_progress,
    }
    return processor(**base_kwargs)

