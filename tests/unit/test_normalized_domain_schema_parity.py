from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa

from backend.models.normalized import (
    NormalizedBuyer,
    NormalizedCategory,
    NormalizedOferta,
    NormalizedOrdenCompra,
    NormalizedOrdenCompraItem,
    NormalizedSupplier,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    REPO_ROOT / "alembic/versions/20260422172140_normalized_domain_normalized_domain_entities.py"
)
MIGRATION_MODULE_NAME = "alembic_version_20260422172140_normalized_domain"


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MIGRATION_MODULE_NAME, MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _index_columns(table: sa.Table) -> dict[str, tuple[str, ...]]:
    return {index.name: tuple(column.name for column in index.columns) for index in table.indexes}


def test_domain_model_index_contracts() -> None:
    assert _index_columns(NormalizedBuyer.__table__) == {
        "ix_normalized_buyers_codigo_unidad_compra": ("codigo_unidad_compra",),
        "ix_normalized_buyers_codigo_organismo_publico": ("codigo_organismo_publico",),
    }
    assert _index_columns(NormalizedSupplier.__table__) == {
        "ix_normalized_suppliers_codigo_proveedor": ("codigo_proveedor",),
        "ix_normalized_suppliers_rut_proveedor": ("rut_proveedor",),
    }
    assert _index_columns(NormalizedCategory.__table__) == {
        "ix_normalized_categories_codigo_categoria": ("codigo_categoria",),
    }

    oferta_indexes = _index_columns(NormalizedOferta.__table__)
    assert oferta_indexes["ix_normalized_ofertas_supplier_key"] == ("supplier_key",)

    orden_compra_indexes = _index_columns(NormalizedOrdenCompra.__table__)
    assert orden_compra_indexes["ix_normalized_ordenes_compra_buyer_key"] == ("buyer_key",)
    assert orden_compra_indexes["ix_normalized_ordenes_compra_supplier_key"] == ("supplier_key",)

    orden_items_indexes = _index_columns(NormalizedOrdenCompraItem.__table__)
    assert orden_items_indexes["ix_normalized_ordenes_compra_items_category_key"] == ("category_key",)


def test_domain_migration_matches_models(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _load_migration_module()
    created_tables: dict[str, tuple[str, ...]] = {}
    created_indexes: dict[str, tuple[str, tuple[str, ...], bool]] = {}
    added_columns: dict[str, list[str]] = {}
    created_foreign_keys: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...]]] = {}

    def _create_table(name: str, *elements: Any, **_: Any) -> None:
        columns = tuple(element.name for element in elements if isinstance(element, sa.Column))
        created_tables[name] = columns

    def _create_index(
        name: str,
        table_name: str,
        columns: list[str],
        *,
        unique: bool = False,
        **_: Any,
    ) -> None:
        created_indexes[name] = (table_name, tuple(columns), unique)

    def _add_column(table_name: str, column: sa.Column, **_: Any) -> None:
        added_columns.setdefault(table_name, []).append(column.name)

    def _create_foreign_key(
        name: str,
        source_table: str,
        referent_table: str,
        local_cols: list[str],
        remote_cols: list[str],
        **_: Any,
    ) -> None:
        created_foreign_keys[name] = (
            source_table,
            referent_table,
            tuple(local_cols),
            tuple(remote_cols),
        )

    monkeypatch.setattr(migration.op, "create_table", _create_table)
    monkeypatch.setattr(migration.op, "create_index", _create_index)
    monkeypatch.setattr(migration.op, "add_column", _add_column)
    monkeypatch.setattr(migration.op, "create_foreign_key", _create_foreign_key)

    migration.upgrade()

    assert created_tables["normalized_buyers"] == tuple(NormalizedBuyer.__table__.columns.keys())
    assert created_tables["normalized_suppliers"] == tuple(NormalizedSupplier.__table__.columns.keys())
    assert created_tables["normalized_categories"] == tuple(NormalizedCategory.__table__.columns.keys())

    expected_new_table_indexes = {
        **_index_columns(NormalizedBuyer.__table__),
        **_index_columns(NormalizedSupplier.__table__),
        **_index_columns(NormalizedCategory.__table__),
    }
    for index_name, expected_columns in expected_new_table_indexes.items():
        table_name, columns, unique = created_indexes[index_name]
        assert unique is False
        assert columns == expected_columns
        assert table_name in {"normalized_buyers", "normalized_suppliers", "normalized_categories"}

    assert {
        "ix_normalized_ordenes_compra_buyer_key": created_indexes["ix_normalized_ordenes_compra_buyer_key"][:2],
        "ix_normalized_ordenes_compra_supplier_key": created_indexes["ix_normalized_ordenes_compra_supplier_key"][:2],
        "ix_normalized_ofertas_supplier_key": created_indexes["ix_normalized_ofertas_supplier_key"][:2],
        "ix_normalized_ordenes_compra_items_category_key": created_indexes[
            "ix_normalized_ordenes_compra_items_category_key"
        ][:2],
    } == {
        "ix_normalized_ordenes_compra_buyer_key": ("normalized_ordenes_compra", ("buyer_key",)),
        "ix_normalized_ordenes_compra_supplier_key": ("normalized_ordenes_compra", ("supplier_key",)),
        "ix_normalized_ofertas_supplier_key": ("normalized_ofertas", ("supplier_key",)),
        "ix_normalized_ordenes_compra_items_category_key": (
            "normalized_ordenes_compra_items",
            ("category_key",),
        ),
    }

    assert {table: tuple(columns) for table, columns in added_columns.items()} == {
        "normalized_ordenes_compra": ("buyer_key", "supplier_key"),
        "normalized_ofertas": ("supplier_key",),
        "normalized_ordenes_compra_items": ("category_key",),
    }

    assert created_foreign_keys == {
        "fk_normalized_ordenes_compra_buyer_key": (
            "normalized_ordenes_compra",
            "normalized_buyers",
            ("buyer_key",),
            ("buyer_key",),
        ),
        "fk_normalized_ordenes_compra_supplier_key": (
            "normalized_ordenes_compra",
            "normalized_suppliers",
            ("supplier_key",),
            ("supplier_key",),
        ),
        "fk_normalized_ofertas_supplier_key": (
            "normalized_ofertas",
            "normalized_suppliers",
            ("supplier_key",),
            ("supplier_key",),
        ),
        "fk_normalized_ordenes_compra_items_category_key": (
            "normalized_ordenes_compra_items",
            "normalized_categories",
            ("category_key",),
            ("category_key",),
        ),
    }

    assert migration.revision == "20260422172140_normalized_domain"
    assert migration.down_revision == "0005_dataset_summary_snapshots"
