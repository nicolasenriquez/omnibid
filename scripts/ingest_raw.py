#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.session import SessionLocal  # noqa: E402
from backend.ingestion.contracts import assert_required_columns  # noqa: E402
from backend.models.operational import (  # noqa: E402
    IngestionBatch,
    PipelineRun,
    PipelineRunStep,
    SourceFile,
)
from backend.models.raw import RawLicitacion, RawOrdenCompra  # noqa: E402
from backend.observability.cli_ui import (  # noqa: E402
    create_progress,
    progress_write,
    timed_step,
)


def log_line(message: str, use_progress: bool) -> None:
    progress_write(message, enabled=use_progress)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def row_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if v == "" or v.upper() == "NA":
        return None
    if v == "1900-01-01":
        return None
    return v


def discover_files(dataset_root: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(dataset_root.glob("licitacion/*.csv")):
        key = ("licitacion", str(path.resolve()))
        if key not in seen:
            files.append(("licitacion", path))
            seen.add(key)
    for path in sorted(dataset_root.glob("orden_compra/*.csv")):
        key = ("orden_compra", str(path.resolve()))
        if key not in seen:
            files.append(("orden_compra", path))
            seen.add(key)
    for path in sorted(dataset_root.glob("orden-compra/*.csv")):
        key = ("orden_compra", str(path.resolve()))
        if key not in seen:
            files.append(("orden_compra", path))
            seen.add(key)
    return files


def resolve_dataset_root(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    env_root = os.getenv("DATASET_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return (Path(__file__).resolve().parents[2] / "dataset-mercado-publico").resolve()


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="latin1", newline="") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        next(reader, None)
        return sum(1 for _ in reader)


def upsert_source_file(session: Session, dataset_type: str, path: Path, sha: str) -> SourceFile:
    existing = session.execute(
        sa.select(SourceFile).where(SourceFile.file_hash_sha256 == sha)
    ).scalar_one_or_none()
    if existing:
        return existing

    source_file = SourceFile(
        dataset_type=dataset_type,
        file_name=path.name,
        file_path=str(path),
        file_size_bytes=path.stat().st_size,
        file_hash_sha256=sha,
        source_modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
        status="registered",
        source_meta={"ingestion_mode": "file_drop"},
    )
    session.add(source_file)
    session.flush()
    return source_file


def create_run(session: Session, dataset_type: str, source_file_id: Any) -> tuple[Any, Any]:
    run = PipelineRun(
        run_key=f"{dataset_type}:{datetime.now(UTC).isoformat()}",
        dataset_type=dataset_type,
        source_file_id=source_file_id,
        status="running",
    )
    session.add(run)
    session.flush()

    step = PipelineRunStep(run_id=run.id, step_name="raw_ingest", status="running")
    session.add(step)
    session.flush()
    return run, step


def create_batch(session: Session, source_file_id: Any, file_name: str) -> IngestionBatch:
    batch = IngestionBatch(
        source_file_id=source_file_id,
        batch_key=f"{file_name}:{datetime.now(UTC).isoformat()}",
        status="started",
    )
    session.add(batch)
    session.flush()
    return batch


def count_raw_rows_for_source_file(session: Session, dataset_type: str, source_file_id: Any) -> int:
    if dataset_type == "licitacion":
        model: Any = RawLicitacion
    else:
        model = RawOrdenCompra

    return int(
        session.execute(
            sa.select(sa.func.count())
            .select_from(model)
            .where(model.source_file_id == source_file_id)
        ).scalar_one()
    )


def build_raw_ingest_metrics(
    *,
    processed_rows: int,
    before_scope_rows: int,
    after_scope_rows: int,
    rejected_rows: int = 0,
) -> dict[str, int]:
    if processed_rows < 0:
        raise ValueError("processed_rows must be >= 0")
    if before_scope_rows < 0:
        raise ValueError("before_scope_rows must be >= 0")
    if after_scope_rows < 0:
        raise ValueError("after_scope_rows must be >= 0")
    if rejected_rows < 0:
        raise ValueError("rejected_rows must be >= 0")
    if after_scope_rows < before_scope_rows:
        raise ValueError("after_scope_rows must be >= before_scope_rows")

    accepted_rows = processed_rows - rejected_rows
    if accepted_rows < 0:
        raise ValueError("accepted_rows cannot be negative")

    deduplicated_rows = accepted_rows
    inserted_delta_rows = after_scope_rows - before_scope_rows
    if inserted_delta_rows > deduplicated_rows:
        raise ValueError("inserted_delta_rows cannot exceed deduplicated_rows")

    existing_or_updated_rows = deduplicated_rows - inserted_delta_rows

    return {
        "processed_rows": processed_rows,
        "rejected_rows": rejected_rows,
        "accepted_rows": accepted_rows,
        "deduplicated_rows": deduplicated_rows,
        "inserted_delta_rows": inserted_delta_rows,
        "existing_or_updated_rows": existing_or_updated_rows,
        "scope_rows_before": before_scope_rows,
        "scope_rows_after": after_scope_rows,
    }


def persist_raw_ingest_failure(
    session: Session,
    batch: IngestionBatch,
    step: PipelineRunStep,
    run: PipelineRun,
    exc: Exception,
) -> None:
    session.rollback()

    batch_any = cast(Any, batch)
    step_any = cast(Any, step)
    run_any = cast(Any, run)

    batch_any.status = "failed"
    batch_any.finished_at = datetime.now(UTC)

    step_any.status = "failed"
    step_any.finished_at = datetime.now(UTC)
    step_any.error_details = {"error": str(exc)}

    run_any.status = "failed"
    run_any.finished_at = datetime.now(UTC)
    run_any.error_summary = str(exc)

    session.commit()


def ingest_file(
    session: Session,
    dataset_type: str,
    path: Path,
    source_file: SourceFile,
    batch: IngestionBatch,
    chunk_size: int,
    show_progress: bool,
    expected_rows: int | None,
) -> int:
    total = 0
    chunk: list[dict[str, Any]] = []
    row_bar = None
    row_bar = create_progress(
        total=expected_rows,
        desc=f"{dataset_type}:{path.name}",
        unit="rows",
        enabled=show_progress,
        leave=False,
        stage="raw",
        footer=True,
        position=2,
    )
    checkpoint_every = max(50_000, chunk_size * 10)
    next_checkpoint = checkpoint_every

    with path.open("r", encoding="latin1", newline="") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        assert_required_columns(dataset_type, list(reader.fieldnames or []), path.name)
        for row_num, row in enumerate(reader, start=1):
            total += 1
            raw = {k: normalize_value(v) for k, v in row.items()}

            if dataset_type == "licitacion":
                payload = {
                    "source_file_id": source_file.id,
                    "batch_id": batch.id,
                    "raw_row_num": row_num,
                    "codigo": raw.get("Codigo"),
                    "codigo_externo": raw.get("CodigoExterno"),
                    "row_hash_sha256": row_hash(raw),
                    "raw_json": raw,
                }
            else:
                payload = {
                    "source_file_id": source_file.id,
                    "batch_id": batch.id,
                    "raw_row_num": row_num,
                    "codigo_oc": raw.get("Codigo"),
                    "codigo_licitacion": raw.get("CodigoLicitacion"),
                    "id_item": raw.get("IDItem"),
                    "row_hash_sha256": row_hash(raw),
                    "raw_json": raw,
                }

            chunk.append(payload)
            if len(chunk) >= chunk_size:
                chunk_len = len(chunk)
                flush_chunk(session, dataset_type, chunk)
                chunk.clear()
                if row_bar is not None:
                    row_bar.update(chunk_len)
                elif total >= next_checkpoint:
                    log_line(f"{path.name}: processed={total:,} rows", show_progress)
                    next_checkpoint += checkpoint_every

    if chunk:
        chunk_len = len(chunk)
        flush_chunk(session, dataset_type, chunk)
        chunk.clear()
        if row_bar is not None:
            row_bar.update(chunk_len)
        elif total >= next_checkpoint:
            log_line(f"{path.name}: processed={total:,} rows", show_progress)
            next_checkpoint += checkpoint_every

    if row_bar is not None:
        row_bar.close()

    return total


def flush_chunk(session: Session, dataset_type: str, chunk: list[dict[str, Any]]) -> None:
    if not chunk:
        return
    if dataset_type == "licitacion":
        stmt = pg_insert(RawLicitacion).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=["source_file_id", "raw_row_num"])
    else:
        stmt = pg_insert(RawOrdenCompra).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=["source_file_id", "raw_row_num"])

    session.execute(stmt)
    session.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Load raw CSV files into raw tables")
    parser.add_argument("--dataset-root", default=None, help="Path to dataset-mercado-publico")
    parser.add_argument(
        "--dataset",
        choices=["licitacion", "orden_compra", "all"],
        default="all",
        help="Which dataset to ingest (default: all — both licitacion and orden_compra)",
    )
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--limit-files", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Reprocess files even if hash exists")
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable progress bars (default: true)",
    )
    parser.add_argument(
        "--precount",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pre-count rows per file to show percentage/ETA in progress bar (default: true)",
    )
    args = parser.parse_args()

    dataset_root = resolve_dataset_root(args.dataset_root)
    if not dataset_root.exists():
        raise SystemExit(f"Dataset root not found: {dataset_root}")

    files = discover_files(dataset_root)
    if args.dataset != "all":
        files = [(dt, p) for dt, p in files if dt == args.dataset]
    if args.limit_files > 0:
        files = files[: args.limit_files]

    files_bar = create_progress(
        total=len(files),
        desc="raw files",
        unit="file",
        enabled=args.progress,
        leave=True,
        stage="raw",
        footer=True,
        position=1,
    )

    with timed_step("raw ingest", enabled=args.progress):
        with SessionLocal() as session:
            for dataset_type, path in files:
                sha = file_sha256(path)
                existing = session.execute(
                    sa.select(SourceFile).where(SourceFile.file_hash_sha256 == sha)
                ).scalar_one_or_none()

                if existing and not args.force:
                    log_line(f"SKIP {path.name}: already loaded (hash match)", args.progress)
                    if files_bar is not None:
                        files_bar.update(1)
                    continue

                source_file = upsert_source_file(session, dataset_type, path, sha)
                run, step = create_run(session, dataset_type, source_file.id)
                batch = create_batch(session, source_file.id, path.name)
                session.commit()

                try:
                    expected_rows = count_csv_rows(path) if args.precount else None
                    before_scope_rows = count_raw_rows_for_source_file(
                        session, dataset_type, source_file.id
                    )
                    with timed_step(f"ingest {path.name}", enabled=args.progress):
                        processed_rows = ingest_file(
                            session=session,
                            dataset_type=dataset_type,
                            path=path,
                            source_file=source_file,
                            batch=batch,
                            chunk_size=args.chunk_size,
                            show_progress=args.progress,
                            expected_rows=expected_rows,
                        )
                    after_scope_rows = count_raw_rows_for_source_file(
                        session, dataset_type, source_file.id
                    )
                    metrics = build_raw_ingest_metrics(
                        processed_rows=processed_rows,
                        before_scope_rows=before_scope_rows,
                        after_scope_rows=after_scope_rows,
                    )

                    batch_any = cast(Any, batch)
                    source_file_any = cast(Any, source_file)
                    step_any = cast(Any, step)
                    run_any = cast(Any, run)

                    batch_any.total_rows = metrics["processed_rows"]
                    batch_any.loaded_rows = metrics["inserted_delta_rows"]
                    batch_any.rejected_rows = metrics["existing_or_updated_rows"]
                    batch_any.status = "completed"
                    batch_any.finished_at = datetime.now(UTC)

                    source_file_any.status = "loaded"
                    source_file_any.source_meta = {
                        **(source_file.source_meta or {}),
                        "raw_ingest_metrics": metrics,
                    }

                    step_any.status = "completed"
                    step_any.finished_at = datetime.now(UTC)
                    step_any.rows_in = metrics["processed_rows"]
                    step_any.rows_out = metrics["inserted_delta_rows"]
                    step_any.rows_rejected = metrics["existing_or_updated_rows"]

                    run_any.config = {
                        **(run.config or {}),
                        "raw_ingest_metrics": metrics,
                    }
                    run_any.status = "completed"
                    run_any.finished_at = datetime.now(UTC)

                    session.commit()
                    log_line(
                        (
                            f"OK {path.name}: "
                            f"processed={metrics['processed_rows']:,} "
                            f"accepted={metrics['accepted_rows']:,} "
                            f"deduplicated={metrics['deduplicated_rows']:,} "
                            f"inserted_delta={metrics['inserted_delta_rows']:,} "
                            f"existing_or_updated={metrics['existing_or_updated_rows']:,}"
                        ),
                        args.progress,
                    )
                    if files_bar is not None:
                        files_bar.update(1)
                except Exception as exc:  # noqa: BLE001
                    persist_raw_ingest_failure(
                        session=session,
                        batch=batch,
                        step=step,
                        run=run,
                        exc=exc,
                    )
                    batch_any = cast(Any, batch)
                    step_any = cast(Any, step)
                    run_any = cast(Any, run)

                    batch_any.status = "failed"
                    batch_any.finished_at = datetime.now(UTC)

                    step_any.status = "failed"
                    step_any.finished_at = datetime.now(UTC)
                    step_any.error_details = {"error": str(exc)}

                    run_any.status = "failed"
                    run_any.finished_at = datetime.now(UTC)
                    run_any.error_summary = str(exc)

                    session.commit()
                    if files_bar is not None:
                        files_bar.update(1)
                    raise

    if files_bar is not None:
        files_bar.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
