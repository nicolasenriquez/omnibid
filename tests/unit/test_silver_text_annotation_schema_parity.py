from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa

from backend.models.normalized import (
    SilverNoticeLineTextAnn,
    SilverNoticeTextAnn,
    SilverPurchaseOrderLineTextAnn,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "alembic/versions/202604230040_silver_text_annotations.py"
MIGRATION_MODULE_NAME = "alembic_version_202604230040_silver_text_ann"


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MIGRATION_MODULE_NAME, MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _index_columns(table: sa.Table) -> dict[str, tuple[str, ...]]:
    return {index.name: tuple(column.name for column in index.columns) for index in table.indexes}


def test_silver_text_annotation_model_index_contracts() -> None:
    assert _index_columns(SilverNoticeTextAnn.__table__) == {
        "ix_silver_notice_text_ann_semantic_category": ("semantic_category_label",),
    }
    assert _index_columns(SilverNoticeLineTextAnn.__table__) == {
        "ix_silver_notice_line_text_ann_semantic_category": ("semantic_category_label",),
    }
    assert _index_columns(SilverPurchaseOrderLineTextAnn.__table__) == {
        "ix_silver_purchase_order_line_text_ann_semantic_category": ("semantic_category_label",),
    }


def test_silver_text_annotation_migration_matches_models(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _load_migration_module()
    created_tables: dict[str, tuple[str, ...]] = {}
    created_indexes: dict[str, tuple[str, tuple[str, ...], bool]] = {}

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

    monkeypatch.setattr(migration.op, "create_table", _create_table)
    monkeypatch.setattr(migration.op, "create_index", _create_index)
    migration.upgrade()

    assert set(created_tables["silver_notice_text_ann"]).issubset(
        set(SilverNoticeTextAnn.__table__.columns.keys())
    )
    assert set(created_tables["silver_notice_line_text_ann"]).issubset(
        set(SilverNoticeLineTextAnn.__table__.columns.keys())
    )
    assert set(created_tables["silver_purchase_order_line_text_ann"]).issubset(
        set(SilverPurchaseOrderLineTextAnn.__table__.columns.keys())
    )

    expected_indexes = {
        **_index_columns(SilverNoticeTextAnn.__table__),
        **_index_columns(SilverNoticeLineTextAnn.__table__),
        **_index_columns(SilverPurchaseOrderLineTextAnn.__table__),
    }
    for index_name, expected_columns in expected_indexes.items():
        table_name, columns, unique = created_indexes[index_name]
        assert unique is False
        assert columns == expected_columns
        assert table_name in {
            "silver_notice_text_ann",
            "silver_notice_line_text_ann",
            "silver_purchase_order_line_text_ann",
        }

    assert migration.revision == "202604230040_silver_text_ann"
    assert migration.down_revision == "202604230030_silver_enrichment"
