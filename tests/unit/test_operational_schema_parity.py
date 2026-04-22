from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa

from backend.models.operational import DatasetSummarySnapshot

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "alembic/versions/0005_dataset_summary_snapshots.py"
MIGRATION_MODULE_NAME = "alembic_version_0005_dataset_summary_snapshots"


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MIGRATION_MODULE_NAME, MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dataset_summary_snapshot_model_index_contract() -> None:
    index_columns = {
        index.name: tuple(column.name for column in index.columns)
        for index in DatasetSummarySnapshot.__table__.indexes
    }
    assert index_columns == {
        "ix_dataset_summary_snapshots_generated_at": ("generated_at",),
        "ix_dataset_summary_snapshots_status_generated_at": ("status", "generated_at"),
    }


def test_dataset_summary_snapshot_migration_matches_model(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _load_migration_module()
    created_tables: dict[str, tuple[str, ...]] = {}
    created_indexes: dict[str, tuple[str, tuple[str, ...]]] = {}

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
        assert unique is False
        created_indexes[name] = (table_name, tuple(columns))

    monkeypatch.setattr(migration.op, "create_table", _create_table)
    monkeypatch.setattr(migration.op, "create_index", _create_index)

    migration.upgrade()

    orm_columns = tuple(DatasetSummarySnapshot.__table__.columns.keys())
    assert created_tables["dataset_summary_snapshots"] == orm_columns

    orm_indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in DatasetSummarySnapshot.__table__.indexes
    }
    migration_indexes = {
        index_name: columns
        for index_name, (table_name, columns) in created_indexes.items()
        if table_name == "dataset_summary_snapshots"
    }
    assert migration_indexes == orm_indexes
    assert migration.revision == "0005_dataset_summary_snapshots"
    assert migration.down_revision == "0004_rename_raw_norm_tables"
