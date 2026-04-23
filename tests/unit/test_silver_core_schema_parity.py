from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa

from backend.models.normalized import (
    SilverAwardOutcome,
    SilverBidSubmission,
    SilverNotice,
    SilverNoticeLine,
    SilverPurchaseOrder,
    SilverPurchaseOrderLine,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "alembic/versions/202604230010_silver_core_entities.py"
MIGRATION_MODULE_NAME = "alembic_version_202604230010_silver_core"


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MIGRATION_MODULE_NAME, MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _index_columns(table: sa.Table) -> dict[str, tuple[str, ...]]:
    return {index.name: tuple(column.name for column in index.columns) for index in table.indexes}


def test_silver_core_model_index_contracts() -> None:
    assert _index_columns(SilverNotice.__table__) == {
        "ix_silver_notice_publication_date": ("publication_date",),
        "ix_silver_notice_status_name": ("notice_status_name",),
    }
    assert _index_columns(SilverNoticeLine.__table__) == {
        "ix_silver_notice_line_notice_id": ("notice_id",),
        "ix_silver_notice_line_onu_product_code": ("onu_product_code",),
    }
    assert _index_columns(SilverBidSubmission.__table__) == {
        "ix_silver_bid_submission_notice_id": ("notice_id",),
        "ix_silver_bid_submission_supplier_key": ("supplier_key",),
    }
    assert _index_columns(SilverAwardOutcome.__table__) == {
        "ix_silver_award_outcome_notice_id": ("notice_id",),
        "ix_silver_award_outcome_supplier_key": ("supplier_key",),
    }
    assert _index_columns(SilverPurchaseOrder.__table__) == {
        "ix_silver_purchase_order_linked_notice_id": ("linked_notice_id",),
        "ix_silver_purchase_order_supplier_key": ("supplier_key",),
        "ix_silver_purchase_order_status_name": ("purchase_order_status_name",),
    }
    assert _index_columns(SilverPurchaseOrderLine.__table__) == {
        "ix_silver_purchase_order_line_order_id": ("purchase_order_id",),
        "ix_silver_purchase_order_line_linked_notice_id": ("linked_notice_id",),
    }


def test_silver_core_migration_matches_models(monkeypatch: pytest.MonkeyPatch) -> None:
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

    assert set(created_tables["silver_notice"]).issubset(set(SilverNotice.__table__.columns.keys()))
    assert set(created_tables["silver_notice_line"]).issubset(
        set(SilverNoticeLine.__table__.columns.keys())
    )
    assert set(created_tables["silver_bid_submission"]).issubset(
        set(SilverBidSubmission.__table__.columns.keys())
    )
    assert set(created_tables["silver_award_outcome"]).issubset(
        set(SilverAwardOutcome.__table__.columns.keys())
    )
    assert set(created_tables["silver_purchase_order"]).issubset(
        set(SilverPurchaseOrder.__table__.columns.keys())
    )
    assert set(created_tables["silver_purchase_order_line"]).issubset(
        set(SilverPurchaseOrderLine.__table__.columns.keys())
    )

    expected_indexes = {
        **_index_columns(SilverNotice.__table__),
        **_index_columns(SilverNoticeLine.__table__),
        **_index_columns(SilverBidSubmission.__table__),
        **_index_columns(SilverAwardOutcome.__table__),
        **_index_columns(SilverPurchaseOrder.__table__),
        **_index_columns(SilverPurchaseOrderLine.__table__),
    }
    for index_name, expected_columns in expected_indexes.items():
        table_name, columns, unique = created_indexes[index_name]
        assert unique is False
        assert columns == expected_columns
        assert table_name in {
            "silver_notice",
            "silver_notice_line",
            "silver_bid_submission",
            "silver_award_outcome",
            "silver_purchase_order",
            "silver_purchase_order_line",
        }

    assert migration.revision == "202604230010_silver_core"
    assert migration.down_revision == "20260422172140_normalized_domain"
