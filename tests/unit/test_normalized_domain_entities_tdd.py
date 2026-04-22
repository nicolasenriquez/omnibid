from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from backend import models as backend_models
from backend.normalized.transform import (
    build_oferta_payload,
    build_orden_compra_item_payload,
    build_orden_compra_payload,
)

ROOT = Path(__file__).resolve().parents[2]
BUILD_NORMALIZED_PATH = ROOT / "scripts" / "build_normalized.py"
SPEC = importlib.util.spec_from_file_location("build_normalized_script", BUILD_NORMALIZED_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load build_normalized module from {BUILD_NORMALIZED_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class _DummyResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _DummySession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.added: list[Any] = []

    def execute(self, _stmt: object) -> _DummyResult:
        self.execute_calls += 1
        return _DummyResult(1)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        return None


def _require_callable(name: str) -> Callable[..., Any]:
    fn = getattr(MODULE, name, None)
    assert callable(fn), f"{name} helper is not implemented"
    return fn


def _require_model(name: str) -> type[Any]:
    model = getattr(backend_models.normalized, name, None)
    assert model is not None, f"{name} model is not implemented"
    return model


def test_identity_helpers_extract_expected_keys_with_typed_supplier_precedence() -> None:
    resolve_buyer_identity_key = _require_callable("resolve_buyer_identity_key")
    resolve_supplier_identity_key = _require_callable("resolve_supplier_identity_key")
    resolve_category_identity_key = _require_callable("resolve_category_identity_key")

    assert resolve_buyer_identity_key({"CodigoUnidadCompra": "  UC-001  "}) == "UC-001"
    assert resolve_buyer_identity_key({"CodigoUnidadCompra": ""}) is None

    assert (
        resolve_supplier_identity_key({"CodigoProveedor": " P-99 ", "RutProveedor": "76.123.456-7"})
        == "codigo:P-99"
    )
    assert (
        resolve_supplier_identity_key({"CodigoProveedor": "", "RutProveedor": " 76.123.456-7 "})
        == "rut:76.123.456-7"
    )
    assert resolve_supplier_identity_key({"CodigoProveedor": "", "RutProveedor": ""}) is None

    assert resolve_category_identity_key({"codigoCategoria": " CAT-1 "}) == "CAT-1"
    assert resolve_category_identity_key({"codigoCategoria": ""}) is None


def test_supplier_domain_for_licitacion_is_gated_by_accepted_oferta_and_sets_fk() -> None:
    build_supplier_domain_from_licitacion_transaction = _require_callable(
        "build_supplier_domain_from_licitacion_transaction"
    )

    raw = {
        "CodigoExterno": "L123",
        "Codigoitem": "1",
        "CodigoProveedor": "P-001",
        "NombreProveedor": "Proveedor Uno",
        "Nombre de la Oferta": "Oferta Uno",
    }
    oferta_payload = build_oferta_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert oferta_payload is not None

    supplier = build_supplier_domain_from_licitacion_transaction(
        raw=raw,
        source_file_id=uuid4(),
        oferta_payload=oferta_payload,
    )
    assert supplier is not None
    assert oferta_payload["supplier_key"] == "codigo:P-001"
    assert supplier["supplier_key"] == "codigo:P-001"

    skipped_supplier = build_supplier_domain_from_licitacion_transaction(
        raw=raw,
        source_file_id=uuid4(),
        oferta_payload=None,
    )
    assert skipped_supplier is None


def test_orden_domain_payloads_are_gated_by_accepted_orden_and_set_fks() -> None:
    build_domain_payloads_from_orden_transaction = _require_callable(
        "build_domain_payloads_from_orden_transaction"
    )

    raw = {
        "Codigo": "OC-1",
        "CodigoUnidadCompra": "UC-1",
        "CodigoProveedor": "P-777",
    }
    orden_payload = build_orden_compra_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert orden_payload is not None

    buyer, supplier = build_domain_payloads_from_orden_transaction(
        raw=raw,
        source_file_id=uuid4(),
        orden_payload=orden_payload,
    )
    assert orden_payload["buyer_key"] == "UC-1"
    assert orden_payload["supplier_key"] == "codigo:P-777"
    assert buyer is not None
    assert supplier is not None

    skipped_buyer, skipped_supplier = build_domain_payloads_from_orden_transaction(
        raw=raw,
        source_file_id=uuid4(),
        orden_payload=None,
    )
    assert skipped_buyer is None
    assert skipped_supplier is None


def test_category_domain_payload_is_gated_by_accepted_item_and_sets_fk() -> None:
    build_category_domain_from_orden_item_transaction = _require_callable(
        "build_category_domain_from_orden_item_transaction"
    )
    raw = {
        "Codigo": "OC-1",
        "IDItem": "1",
        "codigoCategoria": "CAT-9",
    }
    orden_item_payload = build_orden_compra_item_payload(
        raw,
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert orden_item_payload is not None

    category = build_category_domain_from_orden_item_transaction(
        raw=raw,
        source_file_id=uuid4(),
        orden_item_payload=orden_item_payload,
    )
    assert category is not None
    assert orden_item_payload["category_key"] == "CAT-9"
    assert category["category_key"] == "CAT-9"

    skipped_category = build_category_domain_from_orden_item_transaction(
        raw=raw,
        source_file_id=uuid4(),
        orden_item_payload=None,
    )
    assert skipped_category is None


def test_domain_entity_metrics_use_domain_eligibility_processed_rows() -> None:
    build_domain_entity_metrics = _require_callable("build_domain_entity_metrics")
    metrics = build_domain_entity_metrics(
        accepted_rows=7,
        rejected_rows=3,
        deduplicated_rows=6,
        before_scope_rows=100,
        after_scope_rows=104,
    )
    assert metrics["processed_rows"] == 10
    assert metrics["accepted_rows"] == 7
    assert metrics["rejected_rows"] == 3
    assert metrics["inserted_delta_rows"] == 4


def test_licitaciones_flush_chunk_orders_suppliers_before_ofertas(monkeypatch: Any) -> None:
    flush_licitaciones_chunk_buffers = _require_callable("flush_licitaciones_chunk_buffers")
    calls: list[str] = []

    def fake_flush_if_needed(
        _session: Any,
        model: Any,
        _buffer_rows: list[dict[str, Any]],
        _conflict_fields: list[str],
        _chunk_size: int,
        *,
        force: bool = False,
    ) -> int:
        calls.append(model.__name__)
        return 0

    monkeypatch.setattr(MODULE, "flush_if_needed", fake_flush_if_needed)
    flush_licitaciones_chunk_buffers(
        session=_DummySession(),
        chunk_size=100,
        licitaciones_rows=[{"codigo_externo": "L"}],
        licitacion_items_rows=[{"codigo_externo": "L", "codigo_item": "1"}],
        suppliers_rows=[{"supplier_key": "codigo:P-1"}],
        ofertas_rows=[{"oferta_key_sha256": "h" * 64}],
    )

    assert calls == [
        "NormalizedLicitacion",
        "NormalizedLicitacionItem",
        "NormalizedSupplier",
        "NormalizedOferta",
    ]


def test_ordenes_flush_chunk_orders_dimensions_before_facts(monkeypatch: Any) -> None:
    flush_ordenes_chunk_buffers = _require_callable("flush_ordenes_chunk_buffers")
    calls: list[str] = []

    def fake_flush_if_needed(
        _session: Any,
        model: Any,
        _buffer_rows: list[dict[str, Any]],
        _conflict_fields: list[str],
        _chunk_size: int,
        *,
        force: bool = False,
    ) -> int:
        calls.append(model.__name__)
        return 0

    monkeypatch.setattr(MODULE, "flush_if_needed", fake_flush_if_needed)
    flush_ordenes_chunk_buffers(
        session=_DummySession(),
        chunk_size=100,
        buyers_rows=[{"buyer_key": "UC-1"}],
        suppliers_rows=[{"supplier_key": "codigo:P-1"}],
        categories_rows=[{"category_key": "CAT-1"}],
        ordenes_rows=[{"codigo_oc": "OC-1"}],
        ordenes_items_rows=[{"codigo_oc": "OC-1", "id_item": "1"}],
    )

    assert calls == [
        "NormalizedBuyer",
        "NormalizedSupplier",
        "NormalizedCategory",
        "NormalizedOrdenCompra",
        "NormalizedOrdenCompraItem",
    ]


def test_licitaciones_flush_chunk_forces_supplier_flush_when_ofertas_reach_chunk(
    monkeypatch: Any,
) -> None:
    flush_licitaciones_chunk_buffers = _require_callable("flush_licitaciones_chunk_buffers")
    supplier_force_flags: list[bool] = []

    def fake_flush_if_needed(
        _session: Any,
        model: Any,
        _buffer_rows: list[dict[str, Any]],
        _conflict_fields: list[str],
        _chunk_size: int,
        *,
        force: bool = False,
    ) -> int:
        if model.__name__ == "NormalizedSupplier":
            supplier_force_flags.append(force)
        return 0

    monkeypatch.setattr(MODULE, "flush_if_needed", fake_flush_if_needed)
    flush_licitaciones_chunk_buffers(
        session=_DummySession(),
        chunk_size=2,
        licitaciones_rows=[],
        licitacion_items_rows=[],
        suppliers_rows=[{"supplier_key": "codigo:P-1"}],
        ofertas_rows=[{"oferta_key_sha256": "h" * 64}, {"oferta_key_sha256": "i" * 64}],
    )

    assert supplier_force_flags == [True]


def test_ordenes_flush_chunk_forces_dimension_flush_when_facts_reach_chunk(
    monkeypatch: Any,
) -> None:
    flush_ordenes_chunk_buffers = _require_callable("flush_ordenes_chunk_buffers")
    forced_by_model: dict[str, bool] = {}

    def fake_flush_if_needed(
        _session: Any,
        model: Any,
        _buffer_rows: list[dict[str, Any]],
        _conflict_fields: list[str],
        _chunk_size: int,
        *,
        force: bool = False,
    ) -> int:
        forced_by_model[model.__name__] = force
        return 0

    monkeypatch.setattr(MODULE, "flush_if_needed", fake_flush_if_needed)
    flush_ordenes_chunk_buffers(
        session=_DummySession(),
        chunk_size=2,
        buyers_rows=[{"buyer_key": "UC-1"}],
        suppliers_rows=[{"supplier_key": "codigo:P-1"}],
        categories_rows=[{"category_key": "CAT-1"}],
        ordenes_rows=[{"codigo_oc": "OC-1"}, {"codigo_oc": "OC-2"}],
        ordenes_items_rows=[],
    )

    assert forced_by_model["NormalizedBuyer"] is True
    assert forced_by_model["NormalizedSupplier"] is True
    assert forced_by_model["NormalizedCategory"] is True


def test_ordenes_flush_remaining_orders_dimensions_before_facts(monkeypatch: Any) -> None:
    flush_ordenes_remaining_buffers = _require_callable("flush_ordenes_remaining_buffers")
    calls: list[str] = []

    def fake_flush_remaining(
        _session: Any,
        model: Any,
        _buffer_rows: list[dict[str, Any]],
        _conflict_fields: list[str],
    ) -> int:
        calls.append(model.__name__)
        return 0

    monkeypatch.setattr(MODULE, "flush_remaining", fake_flush_remaining)
    flush_ordenes_remaining_buffers(
        session=_DummySession(),
        buyers_rows=[{"buyer_key": "UC-1"}],
        suppliers_rows=[{"supplier_key": "codigo:P-1"}],
        categories_rows=[{"category_key": "CAT-1"}],
        ordenes_rows=[{"codigo_oc": "OC-1"}],
        ordenes_items_rows=[{"codigo_oc": "OC-1", "id_item": "1"}],
    )

    assert calls == [
        "NormalizedBuyer",
        "NormalizedSupplier",
        "NormalizedCategory",
        "NormalizedOrdenCompra",
        "NormalizedOrdenCompraItem",
    ]


def test_domain_conflict_sets_are_explicit_and_stable() -> None:
    assert MODULE.BUYERS_CONFLICT_FIELDS == ["buyer_key"]
    assert MODULE.SUPPLIERS_CONFLICT_FIELDS == ["supplier_key"]
    assert MODULE.CATEGORIES_CONFLICT_FIELDS == ["category_key"]


def test_domain_upsert_deduplicates_duplicate_rows_by_business_key() -> None:
    normalized_buyer_model = _require_model("NormalizedBuyer")
    normalized_supplier_model = _require_model("NormalizedSupplier")

    session = _DummySession()

    buyer_rows = [
        {"buyer_key": "UC-001", "codigo_unidad_compra": "UC-001", "unidad_compra": "old"},
        {"buyer_key": "UC-001", "codigo_unidad_compra": "UC-001", "unidad_compra": "new"},
    ]
    supplier_rows = [
        {"supplier_key": "codigo:P-001", "codigo_proveedor": "P-001", "nombre_proveedor": "old"},
        {"supplier_key": "codigo:P-001", "codigo_proveedor": "P-001", "nombre_proveedor": "new"},
    ]

    buyers_deduplicated = MODULE.upsert_rows(
        session=session,
        model=normalized_buyer_model,
        rows=buyer_rows,
        conflict_fields=["buyer_key"],
    )
    suppliers_deduplicated = MODULE.upsert_rows(
        session=session,
        model=normalized_supplier_model,
        rows=supplier_rows,
        conflict_fields=["supplier_key"],
    )

    assert buyers_deduplicated == 1
    assert suppliers_deduplicated == 1
    assert session.execute_calls == 2


def test_missing_domain_identities_are_tracked_as_quality_issues() -> None:
    entity_metrics = {
        "buyers": {
            "processed_rows": 100,
            "rejected_rows": 4,
            "identity_field": "codigo_unidad_compra",
            "rejection_reason": "missing_identity",
        },
        "suppliers": {
            "processed_rows": 100,
            "rejected_rows": 3,
            "identity_field": "codigo_proveedor_or_rut_proveedor",
            "rejection_reason": "missing_identity",
        },
        "categories": {
            "processed_rows": 100,
            "rejected_rows": 20,
            "identity_field": "codigo_categoria",
            "rejection_reason": "missing_identity",
        },
    }

    issues = MODULE.collect_normalized_quality_issues(entity_metrics)
    by_ref = {str(issue["record_ref"]): issue for issue in issues}

    assert by_ref["buyers"]["table_name"] == "normalized_buyers"
    assert by_ref["buyers"]["issue_type"] == "normalized_missing_domain_identity"
    assert by_ref["buyers"]["column_name"] == "codigo_unidad_compra"
    assert by_ref["suppliers"]["table_name"] == "normalized_suppliers"
    assert by_ref["categories"]["table_name"] == "normalized_categories"


def test_persisted_domain_identity_issues_keep_column_context() -> None:
    session = _DummySession()
    run_id = uuid4()
    issues = [
        {
            "table_name": "normalized_buyers",
            "issue_type": "normalized_missing_domain_identity",
            "severity": "warning",
            "record_ref": "buyers",
            "column_name": "codigo_unidad_compra",
            "details": {"processed_rows": 100, "rejected_rows": 2, "error_rate": 0.02},
        }
    ]

    MODULE.persist_normalized_quality_issues(
        session=session,
        run_id=run_id,
        dataset="licitacion",
        issues=issues,
    )

    assert len(session.added) == 1
    persisted = session.added[0]
    assert persisted.issue_type == "normalized_missing_domain_identity"
    assert persisted.column_name == "codigo_unidad_compra"
