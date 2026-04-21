#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.session import SessionLocal  # noqa: E402
from backend.models.raw import RawLicitacion, RawOrdenCompra  # noqa: E402
from backend.models.normalized import (  # noqa: E402
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedOrdenCompra,
    NormalizedOrdenCompraItem,
)
from backend.normalized.transform import (  # noqa: E402
    build_licitacion_item_payload,
    build_licitacion_payload,
    build_oferta_payload,
    build_orden_compra_item_payload,
    build_orden_compra_payload,
)
from backend.observability.cli_ui import (  # noqa: E402
    create_progress,
    progress_write,
    timed_step,
)

LICITACIONES_CONFLICT_FIELDS = ["codigo_externo"]
LICITACION_ITEMS_CONFLICT_FIELDS = ["codigo_externo", "codigo_item"]
OFERTAS_CONFLICT_FIELDS = ["oferta_key_sha256"]
ORDENES_CONFLICT_FIELDS = ["codigo_oc"]
ORDENES_ITEMS_CONFLICT_FIELDS = ["codigo_oc", "id_item"]
POSTGRES_MAX_BIND_PARAMS = int(os.getenv("NORMALIZED_MAX_BIND_PARAMS", "32767"))
POSTGRES_BIND_PARAM_SAFETY_MARGIN = 64


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def raw_snapshot(session: Session, dataset: str) -> dict[str, int]:
    if dataset == "licitacion":
        model = RawLicitacion
    else:
        model = RawOrdenCompra
    total_rows = session.execute(sa.select(sa.func.count()).select_from(model)).scalar_one()
    max_id = session.execute(sa.select(sa.func.max(model.id))).scalar_one()
    return {"total_rows": int(total_rows or 0), "max_id": int(max_id or 0)}


def should_skip_dataset(state: dict[str, Any], dataset: str, snapshot: dict[str, int]) -> bool:
    dataset_state = state.get(dataset)
    if not isinstance(dataset_state, dict):
        return False
    if dataset_state.get("status") != "completed":
        return False
    return (
        dataset_state.get("source_total_rows") == snapshot["total_rows"]
        and dataset_state.get("source_max_id") == snapshot["max_id"]
    )


def state_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def resolve_start_after_id(dataset_state: dict[str, Any] | None, incremental: bool) -> int:
    if not incremental:
        return 0
    if not isinstance(dataset_state, dict):
        return 0
    if "last_processed_raw_id" in dataset_state:
        return max(0, state_int(dataset_state.get("last_processed_raw_id"), 0))
    return 0


def dedupe_rows(rows: list[dict[str, Any]], key_fields: list[str]) -> list[dict[str, Any]]:
    if not key_fields:
        raise ValueError("conflict key fields cannot be empty")

    latest_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key_values: list[Any] = []
        for field in key_fields:
            value = row.get(field)
            if value is None or value == "":
                raise ValueError(f"missing business key value for field '{field}'")
            key_values.append(value)
        key = tuple(key_values)
        latest_by_key[key] = row
    return list(latest_by_key.values())


def upsert_rows(
    session: Session,
    model: Any,
    rows: list[dict[str, Any]],
    conflict_fields: list[str],
) -> int:
    if not rows:
        return 0

    payloads = dedupe_rows(rows, conflict_fields)
    missing_fields = [field for field in conflict_fields if field not in payloads[0]]
    if missing_fields:
        fields_csv = ", ".join(missing_fields)
        raise ValueError(f"conflict key fields missing from payload: {fields_csv}")

    columns_per_row = max(len(payload) for payload in payloads)
    max_rows_per_stmt = calculate_max_rows_per_upsert(columns_per_row)

    return execute_payloads_with_retry(
        session=session,
        model=model,
        payloads=payloads,
        conflict_fields=conflict_fields,
        max_rows_per_stmt=max_rows_per_stmt,
    )


def execute_payloads_with_retry(
    session: Session,
    model: Any,
    payloads: list[dict[str, Any]],
    conflict_fields: list[str],
    max_rows_per_stmt: int,
) -> int:
    total_upserted = 0
    for start in range(0, len(payloads), max_rows_per_stmt):
        batch_payloads = payloads[start : start + max_rows_per_stmt]
        try:
            total_upserted += execute_single_upsert(
                session=session,
                model=model,
                payloads=batch_payloads,
                conflict_fields=conflict_fields,
            )
        except OperationalError:
            # Split and retry when runtime/driver limits reject large statements.
            if len(batch_payloads) <= 1:
                raise
            smaller_max_rows = max(1, len(batch_payloads) // 2)
            total_upserted += execute_payloads_with_retry(
                session=session,
                model=model,
                payloads=batch_payloads,
                conflict_fields=conflict_fields,
                max_rows_per_stmt=smaller_max_rows,
            )
    return total_upserted


def execute_single_upsert(
    session: Session,
    model: Any,
    payloads: list[dict[str, Any]],
    conflict_fields: list[str],
) -> int:
    stmt = pg_insert(model).values(payloads)

    update_fields = sorted(set(payloads[0].keys()) - set(conflict_fields) - {"created_at"})
    set_map = {field: getattr(stmt.excluded, field) for field in update_fields}
    if "updated_at" in payloads[0]:
        set_map["updated_at"] = sa.func.now()

    if set_map:
        stmt = stmt.on_conflict_do_update(index_elements=conflict_fields, set_=set_map)
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=conflict_fields)

    result = session.execute(stmt)
    return result.rowcount or 0


def calculate_max_rows_per_upsert(columns_per_row: int) -> int:
    if columns_per_row <= 0:
        raise ValueError("columns_per_row must be > 0")
    available_params = POSTGRES_MAX_BIND_PARAMS - POSTGRES_BIND_PARAM_SAFETY_MARGIN
    return max(1, available_params // columns_per_row)


def flush_if_needed(
    session: Session,
    model: Any,
    buffer_rows: list[dict[str, Any]],
    conflict_fields: list[str],
    chunk_size: int,
) -> int:
    if len(buffer_rows) < chunk_size:
        return 0
    upserted = upsert_rows(session, model, buffer_rows, conflict_fields)
    buffer_rows.clear()
    return upserted


def flush_remaining(
    session: Session,
    model: Any,
    buffer_rows: list[dict[str, Any]],
    conflict_fields: list[str],
) -> int:
    if not buffer_rows:
        return 0
    upserted = upsert_rows(session, model, buffer_rows, conflict_fields)
    buffer_rows.clear()
    return upserted


def process_licitaciones(
    session: Session,
    fetch_size: int,
    chunk_size: int,
    limit_rows: int,
    show_progress: bool,
    start_after_id: int = 0,
    on_checkpoint: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    total_rows = session.execute(
        sa.select(sa.func.count())
        .select_from(RawLicitacion)
        .where(RawLicitacion.id > start_after_id)
    ).scalar_one()
    target_rows = min(total_rows, limit_rows) if limit_rows > 0 else total_rows

    progress_write(
        "[normalized] licitaciones raw rows "
        f"(delta id > {start_after_id:,}): {total_rows:,}, target: {target_rows:,}",
        enabled=show_progress,
    )

    last_id = start_after_id
    processed = 0

    licitaciones_rows: list[dict[str, Any]] = []
    licitacion_items_rows: list[dict[str, Any]] = []
    ofertas_rows: list[dict[str, Any]] = []
    licitaciones_rejected = 0
    licitacion_items_rejected = 0
    ofertas_rejected = 0
    licitaciones_upserted = 0
    licitacion_items_upserted = 0
    ofertas_upserted = 0

    row_bar = create_progress(
        total=target_rows,
        desc="normalized licitaciones",
        unit="rows",
        enabled=show_progress,
        leave=True,
        stage="normalized",
        footer=True,
        position=1,
    )
    checkpoint_every = max(10_000, fetch_size)
    next_checkpoint = checkpoint_every
    state_checkpoint_every = max(50_000, fetch_size * 5)
    next_state_checkpoint = state_checkpoint_every
    try:
        while True:
            if limit_rows > 0 and processed >= limit_rows:
                break

            page_limit = fetch_size
            if limit_rows > 0:
                remaining = limit_rows - processed
                if remaining < page_limit:
                    page_limit = remaining

            batch = (
                session.execute(
                    sa.select(RawLicitacion)
                    .where(RawLicitacion.id > last_id)
                    .order_by(RawLicitacion.id.asc())
                    .limit(page_limit)
                )
                .scalars()
                .all()
            )
            if not batch:
                break

            for raw_row in batch:
                last_id = raw_row.id
                processed += 1
                raw = raw_row.raw_json or {}

                lic = build_licitacion_payload(
                    raw=raw,
                    source_file_id=raw_row.source_file_id,
                    row_hash_sha256=raw_row.row_hash_sha256,
                )
                if lic is not None:
                    licitaciones_rows.append(lic)
                else:
                    licitaciones_rejected += 1

                lic_item = build_licitacion_item_payload(
                    raw=raw,
                    source_file_id=raw_row.source_file_id,
                    row_hash_sha256=raw_row.row_hash_sha256,
                )
                if lic_item is not None:
                    licitacion_items_rows.append(lic_item)
                else:
                    licitacion_items_rejected += 1

                oferta = build_oferta_payload(
                    raw=raw,
                    source_file_id=raw_row.source_file_id,
                    row_hash_sha256=raw_row.row_hash_sha256,
                )
                if oferta is not None:
                    ofertas_rows.append(oferta)
                else:
                    ofertas_rejected += 1

                licitaciones_upserted += flush_if_needed(
                    session,
                    NormalizedLicitacion,
                    licitaciones_rows,
                    LICITACIONES_CONFLICT_FIELDS,
                    chunk_size,
                )
                licitacion_items_upserted += flush_if_needed(
                    session,
                    NormalizedLicitacionItem,
                    licitacion_items_rows,
                    LICITACION_ITEMS_CONFLICT_FIELDS,
                    chunk_size,
                )
                ofertas_upserted += flush_if_needed(
                    session,
                    NormalizedOferta,
                    ofertas_rows,
                    OFERTAS_CONFLICT_FIELDS,
                    chunk_size,
                )

            session.commit()
            if row_bar is not None:
                row_bar.update(len(batch))
            else:
                if processed >= next_checkpoint or processed == target_rows:
                    progress_write(
                        f"[normalized] licitaciones progress: {processed:,}/{target_rows:,}",
                        enabled=show_progress,
                    )
                    next_checkpoint += checkpoint_every

            if on_checkpoint is not None and (processed >= next_state_checkpoint):
                on_checkpoint(last_id, processed)
                next_state_checkpoint += state_checkpoint_every
    finally:
        if row_bar is not None:
            row_bar.close()

    licitaciones_upserted += flush_remaining(
        session,
        NormalizedLicitacion,
        licitaciones_rows,
        LICITACIONES_CONFLICT_FIELDS,
    )
    licitacion_items_upserted += flush_remaining(
        session,
        NormalizedLicitacionItem,
        licitacion_items_rows,
        LICITACION_ITEMS_CONFLICT_FIELDS,
    )
    ofertas_upserted += flush_remaining(
        session,
        NormalizedOferta,
        ofertas_rows,
        OFERTAS_CONFLICT_FIELDS,
    )

    session.commit()
    progress_write(
        "[normalized] licitaciones summary: "
        f"processed={processed:,}, "
        f"rejected(header/items/ofertas)="
        f"{licitaciones_rejected:,}/{licitacion_items_rejected:,}/{ofertas_rejected:,}, "
        f"upserted(header/items/ofertas)="
        f"{licitaciones_upserted:,}/{licitacion_items_upserted:,}/{ofertas_upserted:,}"
        ,
        enabled=show_progress,
    )
    progress_write("[normalized] licitaciones done", enabled=show_progress)
    if on_checkpoint is not None:
        on_checkpoint(last_id, processed)
    return {"processed_rows": processed, "last_raw_id": last_id}


def process_ordenes_compra(
    session: Session,
    fetch_size: int,
    chunk_size: int,
    limit_rows: int,
    show_progress: bool,
    start_after_id: int = 0,
    on_checkpoint: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    total_rows = session.execute(
        sa.select(sa.func.count())
        .select_from(RawOrdenCompra)
        .where(RawOrdenCompra.id > start_after_id)
    ).scalar_one()
    target_rows = min(total_rows, limit_rows) if limit_rows > 0 else total_rows

    progress_write(
        "[normalized] ordenes_compra raw rows "
        f"(delta id > {start_after_id:,}): {total_rows:,}, target: {target_rows:,}",
        enabled=show_progress,
    )

    last_id = start_after_id
    processed = 0

    ordenes_rows: list[dict[str, Any]] = []
    ordenes_items_rows: list[dict[str, Any]] = []
    ordenes_rejected = 0
    ordenes_items_rejected = 0
    ordenes_upserted = 0
    ordenes_items_upserted = 0

    row_bar = create_progress(
        total=target_rows,
        desc="normalized ordenes_compra",
        unit="rows",
        enabled=show_progress,
        leave=True,
        stage="normalized",
        footer=True,
        position=1,
    )
    checkpoint_every = max(10_000, fetch_size)
    next_checkpoint = checkpoint_every
    state_checkpoint_every = max(50_000, fetch_size * 5)
    next_state_checkpoint = state_checkpoint_every
    try:
        while True:
            if limit_rows > 0 and processed >= limit_rows:
                break

            page_limit = fetch_size
            if limit_rows > 0:
                remaining = limit_rows - processed
                if remaining < page_limit:
                    page_limit = remaining

            batch = (
                session.execute(
                    sa.select(RawOrdenCompra)
                    .where(RawOrdenCompra.id > last_id)
                    .order_by(RawOrdenCompra.id.asc())
                    .limit(page_limit)
                )
                .scalars()
                .all()
            )
            if not batch:
                break

            for raw_row in batch:
                last_id = raw_row.id
                processed += 1
                raw = raw_row.raw_json or {}

                orden = build_orden_compra_payload(
                    raw=raw,
                    source_file_id=raw_row.source_file_id,
                    row_hash_sha256=raw_row.row_hash_sha256,
                )
                if orden is not None:
                    ordenes_rows.append(orden)
                else:
                    ordenes_rejected += 1

                orden_item = build_orden_compra_item_payload(
                    raw=raw,
                    source_file_id=raw_row.source_file_id,
                    row_hash_sha256=raw_row.row_hash_sha256,
                )
                if orden_item is not None:
                    ordenes_items_rows.append(orden_item)
                else:
                    ordenes_items_rejected += 1

                ordenes_upserted += flush_if_needed(
                    session,
                    NormalizedOrdenCompra,
                    ordenes_rows,
                    ORDENES_CONFLICT_FIELDS,
                    chunk_size,
                )
                ordenes_items_upserted += flush_if_needed(
                    session,
                    NormalizedOrdenCompraItem,
                    ordenes_items_rows,
                    ORDENES_ITEMS_CONFLICT_FIELDS,
                    chunk_size,
                )

            session.commit()
            if row_bar is not None:
                row_bar.update(len(batch))
            else:
                if processed >= next_checkpoint or processed == target_rows:
                    progress_write(
                        f"[normalized] ordenes_compra progress: {processed:,}/{target_rows:,}",
                        enabled=show_progress,
                    )
                    next_checkpoint += checkpoint_every

            if on_checkpoint is not None and (processed >= next_state_checkpoint):
                on_checkpoint(last_id, processed)
                next_state_checkpoint += state_checkpoint_every
    finally:
        if row_bar is not None:
            row_bar.close()

    ordenes_upserted += flush_remaining(
        session,
        NormalizedOrdenCompra,
        ordenes_rows,
        ORDENES_CONFLICT_FIELDS,
    )
    ordenes_items_upserted += flush_remaining(
        session,
        NormalizedOrdenCompraItem,
        ordenes_items_rows,
        ORDENES_ITEMS_CONFLICT_FIELDS,
    )

    session.commit()
    progress_write(
        "[normalized] ordenes_compra summary: "
        f"processed={processed:,}, "
        f"rejected(header/items)={ordenes_rejected:,}/{ordenes_items_rejected:,}, "
        f"upserted(header/items)={ordenes_upserted:,}/{ordenes_items_upserted:,}"
        ,
        enabled=show_progress,
    )
    progress_write("[normalized] ordenes_compra done", enabled=show_progress)
    if on_checkpoint is not None:
        on_checkpoint(last_id, processed)
    return {"processed_rows": processed, "last_raw_id": last_id}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build normalized tables from raw datasets")
    parser.add_argument(
        "--dataset",
        choices=["all", "licitacion", "orden_compra"],
        default="all",
        help="Dataset to process",
    )
    parser.add_argument("--fetch-size", type=int, default=10_000, help="Rows fetched per page")
    parser.add_argument("--chunk-size", type=int, default=500, help="Rows per upsert chunk")
    parser.add_argument(
        "--limit-rows",
        type=int,
        default=0,
        help="Limit raw rows processed per dataset (0 means all)",
    )
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable progress bars and timed stage logs (default: true)",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume/skip completed dataset phases using state file (default: true)",
    )
    parser.add_argument(
        "--incremental",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Process only new raw rows (id > last_processed_raw_id) per dataset "
            "(default: true)"
        ),
    )
    parser.add_argument(
        "--state-path",
        default="data/runtime/normalized_build_state.json",
        help="State file path for resumable dataset phases",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Clear existing normalized state file before processing",
    )
    args = parser.parse_args()
    if args.fetch_size <= 0:
        raise ValueError("--fetch-size must be > 0")
    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")
    if args.limit_rows < 0:
        raise ValueError("--limit-rows must be >= 0")
    if args.chunk_size > 5000:
        progress_write(
            "[normalized] warning: large chunk-size may increase statement failures; consider <= 1000",
            enabled=args.progress,
        )

    state_path = Path(args.state_path).expanduser().resolve()
    if args.reset_state and state_path.exists():
        state_path.unlink()
    state = load_state(state_path)

    datasets: list[str]
    if args.dataset == "all":
        datasets = ["licitacion", "orden_compra"]
    else:
        datasets = [args.dataset]

    with SessionLocal() as session:
        for dataset in datasets:
            dataset_state = state.get(dataset)
            if not isinstance(dataset_state, dict):
                dataset_state = {}
            snapshot = raw_snapshot(session, dataset)
            if args.resume and should_skip_dataset(state, dataset, snapshot):
                progress_write(
                    f"[normalized] skip {dataset}: source snapshot unchanged and dataset already completed",
                    enabled=args.progress,
                )
                continue

            start_after_id = resolve_start_after_id(dataset_state, incremental=args.incremental)
            mode_label = "incremental" if args.incremental else "full"
            progress_write(
                f"[normalized] dataset={dataset} mode={mode_label} start_after_id={start_after_id:,}",
                enabled=args.progress,
            )

            state[dataset] = {
                "status": "running",
                "source_total_rows": snapshot["total_rows"],
                "source_max_id": snapshot["max_id"],
                "mode": mode_label,
                "start_after_id": start_after_id,
                "last_processed_raw_id": start_after_id,
                "processed_rows_current_run": 0,
            }
            save_state(state_path, state)

            def persist_checkpoint(last_raw_id: int, processed_rows: int) -> None:
                current = state.get(dataset)
                if not isinstance(current, dict):
                    return
                current["last_processed_raw_id"] = max(
                    state_int(current.get("last_processed_raw_id"), 0),
                    max(0, last_raw_id),
                )
                current["processed_rows_current_run"] = processed_rows
                save_state(state_path, state)

            try:
                with timed_step(f"normalized dataset={dataset}", enabled=args.progress):
                    if dataset == "licitacion":
                        metrics = process_licitaciones(
                            session=session,
                            fetch_size=args.fetch_size,
                            chunk_size=args.chunk_size,
                            limit_rows=args.limit_rows,
                            show_progress=args.progress,
                            start_after_id=start_after_id,
                            on_checkpoint=persist_checkpoint,
                        )
                    else:
                        metrics = process_ordenes_compra(
                            session=session,
                            fetch_size=args.fetch_size,
                            chunk_size=args.chunk_size,
                            limit_rows=args.limit_rows,
                            show_progress=args.progress,
                            start_after_id=start_after_id,
                            on_checkpoint=persist_checkpoint,
                        )

                last_processed_raw_id = max(
                    state_int(metrics.get("last_raw_id"), start_after_id),
                    start_after_id,
                )
                state[dataset] = {
                    "status": "completed",
                    "source_total_rows": snapshot["total_rows"],
                    "source_max_id": snapshot["max_id"],
                    "mode": mode_label,
                    "start_after_id": start_after_id,
                    "processed_rows_last_run": metrics["processed_rows"],
                    "processed_rows_current_run": metrics["processed_rows"],
                    "processed_rows_total": state_int(dataset_state.get("processed_rows_total"), 0)
                    + state_int(metrics.get("processed_rows"), 0),
                    "last_processed_raw_id": last_processed_raw_id,
                    "last_raw_id": metrics["last_raw_id"],
                }
                save_state(state_path, state)
            except Exception:
                failed_state = state.get(dataset)
                if not isinstance(failed_state, dict):
                    failed_state = {}
                failed_state["status"] = "failed"
                failed_state["source_total_rows"] = snapshot["total_rows"]
                failed_state["source_max_id"] = snapshot["max_id"]
                state[dataset] = failed_state
                save_state(state_path, state)
                raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
