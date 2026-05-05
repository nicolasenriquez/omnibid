from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.models.normalized import (
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedOrdenCompra,
    NormalizedOrdenCompraItem,
)
from backend.models.operational import SourceFile
from backend.models.raw import RawLicitacion, RawOrdenCompra

DATASET_SUMMARY_MODELS: tuple[tuple[str, type[Any]], ...] = (
    ("source_files_count", SourceFile),
    ("raw_licitaciones_count", RawLicitacion),
    ("raw_ordenes_compra_count", RawOrdenCompra),
    ("normalized_licitaciones_count", NormalizedLicitacion),
    ("normalized_licitacion_items_count", NormalizedLicitacionItem),
    ("normalized_ofertas_count", NormalizedOferta),
    ("normalized_ordenes_compra_count", NormalizedOrdenCompra),
    ("normalized_ordenes_compra_items_count", NormalizedOrdenCompraItem),
)


def count_rows(db: Session, model: type[Any]) -> int:
    return int(db.execute(sa.select(sa.func.count()).select_from(model)).scalar_one())


def compute_dataset_summary_counts(db: Session) -> dict[str, int]:
    return {summary_key: count_rows(db, model) for summary_key, model in DATASET_SUMMARY_MODELS}
