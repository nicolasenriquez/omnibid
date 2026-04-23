from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa

from backend.models.normalized import (
    SilverBuyingOrg,
    SilverCategoryRef,
    SilverContractingUnit,
    SilverNoticePurchaseOrderLink,
    SilverSupplier,
    SilverSupplierParticipation,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "alembic/versions/202604230020_silver_master_bridge_entities.py"
MIGRATION_MODULE_NAME = "alembic_version_202604230020_silver_master_bridge"


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MIGRATION_MODULE_NAME, MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _index_columns(table: sa.Table) -> dict[str, tuple[str, ...]]:
    return {index.name: tuple(column.name for column in index.columns) for index in table.indexes}


def test_silver_master_bridge_model_index_contracts() -> None:
    assert _index_columns(SilverBuyingOrg.__table__) == {
        "ix_silver_buying_org_name": ("buying_org_name",),
    }
    assert _index_columns(SilverContractingUnit.__table__) == {
        "ix_silver_contracting_unit_buying_org_id": ("buying_org_id",),
        "ix_silver_contracting_unit_unit_rut": ("unit_rut",),
    }
    assert _index_columns(SilverSupplier.__table__) == {
        "ix_silver_supplier_supplier_rut": ("supplier_rut",),
        "ix_silver_supplier_supplier_branch_id": ("supplier_branch_id",),
    }
    assert _index_columns(SilverCategoryRef.__table__) == {
        "ix_silver_category_ref_onu_product_code": ("onu_product_code",),
        "ix_silver_category_ref_category_code": ("category_code",),
    }
    assert _index_columns(SilverNoticePurchaseOrderLink.__table__) == {
        "ix_silver_notice_purchase_order_link_notice_id": ("notice_id",),
        "ix_silver_notice_purchase_order_link_purchase_order_id": ("purchase_order_id",),
    }
    assert _index_columns(SilverSupplierParticipation.__table__) == {
        "ix_silver_supplier_participation_supplier_id": ("supplier_id",),
        "ix_silver_supplier_participation_notice_id": ("notice_id",),
    }


def test_silver_master_bridge_migration_matches_models(monkeypatch: pytest.MonkeyPatch) -> None:
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

    assert set(created_tables["silver_buying_org"]).issubset(
        set(SilverBuyingOrg.__table__.columns.keys())
    )
    assert set(created_tables["silver_contracting_unit"]).issubset(
        set(SilverContractingUnit.__table__.columns.keys())
    )
    assert set(created_tables["silver_supplier"]).issubset(
        set(SilverSupplier.__table__.columns.keys())
    )
    assert set(created_tables["silver_category_ref"]).issubset(
        set(SilverCategoryRef.__table__.columns.keys())
    )
    assert set(created_tables["silver_notice_purchase_order_link"]).issubset(
        set(SilverNoticePurchaseOrderLink.__table__.columns.keys())
    )
    assert set(created_tables["silver_supplier_participation"]).issubset(
        set(SilverSupplierParticipation.__table__.columns.keys())
    )

    expected_indexes = {
        **_index_columns(SilverBuyingOrg.__table__),
        **_index_columns(SilverContractingUnit.__table__),
        **_index_columns(SilverSupplier.__table__),
        **_index_columns(SilverCategoryRef.__table__),
        **_index_columns(SilverNoticePurchaseOrderLink.__table__),
        **_index_columns(SilverSupplierParticipation.__table__),
    }
    for index_name, expected_columns in expected_indexes.items():
        table_name, columns, unique = created_indexes[index_name]
        assert unique is False
        assert columns == expected_columns
        assert table_name in {
            "silver_buying_org",
            "silver_contracting_unit",
            "silver_supplier",
            "silver_category_ref",
            "silver_notice_purchase_order_link",
            "silver_supplier_participation",
        }

    assert migration.revision == "202604230020_silver_master"
    assert migration.down_revision == "202604230010_silver_core"
