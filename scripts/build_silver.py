#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.session import SessionLocal  # noqa: E402
from backend.models.bronze import BronzeLicitacionesRaw, BronzeOrdenesCompraRaw  # noqa: E402
from backend.models.silver import (  # noqa: E402
    SilverLicitacion,
    SilverLicitacionItem,
    SilverOferta,
    SilverOrdenCompra,
    SilverOrdenCompraItem,
)
from backend.silver.transform import (  # noqa: E402
    build_licitacion_item_payload,
    build_licitacion_payload,
    build_oferta_payload,
    build_orden_compra_item_payload,
    build_orden_compra_payload,
)

LICITACIONES_CONFLICT_FIELDS = ["codigo_externo"]
LICITACION_ITEMS_CONFLICT_FIELDS = ["codigo_externo", "codigo_item"]
OFERTAS_CONFLICT_FIELDS = ["oferta_key_sha256"]
ORDENES_CONFLICT_FIELDS = ["codigo_oc"]
ORDENES_ITEMS_CONFLICT_FIELDS = ["codigo_oc", "id_item"]


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
) -> None:
    total_rows = session.execute(
        sa.select(sa.func.count()).select_from(BronzeLicitacionesRaw)
    ).scalar_one()
    target_rows = min(total_rows, limit_rows) if limit_rows > 0 else total_rows

    print(f"[silver] licitaciones bronze rows: {total_rows:,}, target: {target_rows:,}")

    last_id = 0
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
                sa.select(BronzeLicitacionesRaw)
                .where(BronzeLicitacionesRaw.id > last_id)
                .order_by(BronzeLicitacionesRaw.id.asc())
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
                SilverLicitacion,
                licitaciones_rows,
                LICITACIONES_CONFLICT_FIELDS,
                chunk_size,
            )
            licitacion_items_upserted += flush_if_needed(
                session,
                SilverLicitacionItem,
                licitacion_items_rows,
                LICITACION_ITEMS_CONFLICT_FIELDS,
                chunk_size,
            )
            ofertas_upserted += flush_if_needed(
                session,
                SilverOferta,
                ofertas_rows,
                OFERTAS_CONFLICT_FIELDS,
                chunk_size,
            )

        session.commit()
        print(f"[silver] licitaciones progress: {processed:,}/{target_rows:,}")

    licitaciones_upserted += flush_remaining(
        session,
        SilverLicitacion,
        licitaciones_rows,
        LICITACIONES_CONFLICT_FIELDS,
    )
    licitacion_items_upserted += flush_remaining(
        session,
        SilverLicitacionItem,
        licitacion_items_rows,
        LICITACION_ITEMS_CONFLICT_FIELDS,
    )
    ofertas_upserted += flush_remaining(
        session,
        SilverOferta,
        ofertas_rows,
        OFERTAS_CONFLICT_FIELDS,
    )

    session.commit()
    print(
        "[silver] licitaciones summary: "
        f"processed={processed:,}, "
        f"rejected(header/items/ofertas)="
        f"{licitaciones_rejected:,}/{licitacion_items_rejected:,}/{ofertas_rejected:,}, "
        f"upserted(header/items/ofertas)="
        f"{licitaciones_upserted:,}/{licitacion_items_upserted:,}/{ofertas_upserted:,}"
    )
    print("[silver] licitaciones done")


def process_ordenes_compra(
    session: Session,
    fetch_size: int,
    chunk_size: int,
    limit_rows: int,
) -> None:
    total_rows = session.execute(
        sa.select(sa.func.count()).select_from(BronzeOrdenesCompraRaw)
    ).scalar_one()
    target_rows = min(total_rows, limit_rows) if limit_rows > 0 else total_rows

    print(f"[silver] ordenes_compra bronze rows: {total_rows:,}, target: {target_rows:,}")

    last_id = 0
    processed = 0

    ordenes_rows: list[dict[str, Any]] = []
    ordenes_items_rows: list[dict[str, Any]] = []
    ordenes_rejected = 0
    ordenes_items_rejected = 0
    ordenes_upserted = 0
    ordenes_items_upserted = 0

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
                sa.select(BronzeOrdenesCompraRaw)
                .where(BronzeOrdenesCompraRaw.id > last_id)
                .order_by(BronzeOrdenesCompraRaw.id.asc())
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
                SilverOrdenCompra,
                ordenes_rows,
                ORDENES_CONFLICT_FIELDS,
                chunk_size,
            )
            ordenes_items_upserted += flush_if_needed(
                session,
                SilverOrdenCompraItem,
                ordenes_items_rows,
                ORDENES_ITEMS_CONFLICT_FIELDS,
                chunk_size,
            )

        session.commit()
        print(f"[silver] ordenes_compra progress: {processed:,}/{target_rows:,}")

    ordenes_upserted += flush_remaining(
        session,
        SilverOrdenCompra,
        ordenes_rows,
        ORDENES_CONFLICT_FIELDS,
    )
    ordenes_items_upserted += flush_remaining(
        session,
        SilverOrdenCompraItem,
        ordenes_items_rows,
        ORDENES_ITEMS_CONFLICT_FIELDS,
    )

    session.commit()
    print(
        "[silver] ordenes_compra summary: "
        f"processed={processed:,}, "
        f"rejected(header/items)={ordenes_rejected:,}/{ordenes_items_rejected:,}, "
        f"upserted(header/items)={ordenes_upserted:,}/{ordenes_items_upserted:,}"
    )
    print("[silver] ordenes_compra done")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Silver tables from Bronze raw datasets")
    parser.add_argument(
        "--dataset",
        choices=["all", "licitacion", "orden_compra"],
        default="all",
        help="Dataset to process",
    )
    parser.add_argument("--fetch-size", type=int, default=10_000, help="Rows fetched per page")
    parser.add_argument("--chunk-size", type=int, default=2_000, help="Rows per upsert chunk")
    parser.add_argument(
        "--limit-rows",
        type=int,
        default=0,
        help="Limit Bronze rows processed per dataset (0 means all)",
    )
    args = parser.parse_args()
    if args.fetch_size <= 0:
        raise ValueError("--fetch-size must be > 0")
    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")
    if args.limit_rows < 0:
        raise ValueError("--limit-rows must be >= 0")

    with SessionLocal() as session:
        if args.dataset in {"all", "licitacion"}:
            process_licitaciones(
                session=session,
                fetch_size=args.fetch_size,
                chunk_size=args.chunk_size,
                limit_rows=args.limit_rows,
            )
        if args.dataset in {"all", "orden_compra"}:
            process_ordenes_compra(
                session=session,
                fetch_size=args.fetch_size,
                chunk_size=args.chunk_size,
                limit_rows=args.limit_rows,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
