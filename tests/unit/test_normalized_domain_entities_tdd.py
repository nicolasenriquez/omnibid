from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import pytest

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


class _RecordingSession(_DummySession):
    def __init__(self) -> None:
        super().__init__()
        self.statements: list[str] = []

    def execute(self, stmt: object) -> _DummyResult:
        self.execute_calls += 1
        self.statements.append(str(stmt))
        return _DummyResult(1)


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
    assert resolve_category_identity_key({"codigoCategoria": "", "codigoProductoONU": " 10101504 "}) == "onu:10101504"
    assert resolve_category_identity_key({"codigoCategoria": "", "CodigoProductoONU": " 10101505 "}) == "onu:10101505"
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


def test_category_domain_payload_uses_onu_fallback_identity_when_category_code_missing() -> None:
    build_category_domain_from_orden_item_transaction = _require_callable(
        "build_category_domain_from_orden_item_transaction"
    )
    raw = {
        "Codigo": "OC-2",
        "IDItem": "2",
        "codigoCategoria": "",
        "codigoProductoONU": "10101504",
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
    assert orden_item_payload["category_key"] == "onu:10101504"
    assert category["category_key"] == "onu:10101504"
    assert category["codigo_categoria"] == "onu:10101504"


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


def test_silver_conflict_contracts_are_explicit() -> None:
    assert MODULE.SILVER_NOTICE_CONFLICT_FIELDS == ["notice_id"]
    assert MODULE.SILVER_NOTICE_LINE_CONFLICT_FIELDS == ["notice_id", "item_code"]
    assert MODULE.SILVER_BID_SUBMISSION_CONFLICT_FIELDS == ["bid_submission_id"]
    assert MODULE.SILVER_AWARD_OUTCOME_CONFLICT_FIELDS == ["award_outcome_id"]
    assert MODULE.SILVER_PURCHASE_ORDER_CONFLICT_FIELDS == ["purchase_order_id"]
    assert MODULE.SILVER_PURCHASE_ORDER_LINE_CONFLICT_FIELDS == ["purchase_order_id", "line_item_id"]
    assert MODULE.SILVER_BUYING_ORG_CONFLICT_FIELDS == ["buying_org_id"]
    assert MODULE.SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS == ["contracting_unit_id"]
    assert MODULE.SILVER_SUPPLIER_CONFLICT_FIELDS == ["supplier_id"]
    assert MODULE.SILVER_CATEGORY_REF_CONFLICT_FIELDS == ["category_ref_id"]
    assert MODULE.SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS == [
        "notice_id",
        "purchase_order_id",
        "link_type",
    ]
    assert MODULE.SILVER_SUPPLIER_PARTICIPATION_CONFLICT_FIELDS == ["supplier_id", "notice_id"]
    assert MODULE.SILVER_NOTICE_TEXT_ANN_CONFLICT_FIELDS == ["notice_id", "nlp_version"]
    assert MODULE.SILVER_NOTICE_LINE_TEXT_ANN_CONFLICT_FIELDS == ["notice_id", "item_code", "nlp_version"]
    assert MODULE.SILVER_PURCHASE_ORDER_LINE_TEXT_ANN_CONFLICT_FIELDS == [
        "purchase_order_id",
        "line_item_id",
        "nlp_version",
    ]


def test_silver_purchase_order_upsert_deduplicates_by_business_key() -> None:
    rows = [
        {"purchase_order_id": "OC-1", "purchase_order_status_name": "Enviada"},
        {"purchase_order_id": "OC-1", "purchase_order_status_name": "Aceptada"},
        {"purchase_order_id": "OC-2", "purchase_order_status_name": "Aceptada"},
    ]
    dummy = _DummySession()

    deduplicated = MODULE.upsert_rows(
        dummy,
        _require_model("SilverPurchaseOrder"),
        rows,
        MODULE.SILVER_PURCHASE_ORDER_CONFLICT_FIELDS,
    )

    assert deduplicated == 2
    assert dummy.execute_calls == 1


def test_silver_link_upsert_deduplicates_by_notice_po_link_key() -> None:
    rows = [
        {
            "notice_id": "N-1",
            "purchase_order_id": "OC-1",
            "link_type": "explicit_code_match",
        },
        {
            "notice_id": "N-1",
            "purchase_order_id": "OC-1",
            "link_type": "explicit_code_match",
            "source_system": "mercado_publico_csv",
        },
    ]
    dummy = _DummySession()

    deduplicated = MODULE.upsert_rows(
        dummy,
        _require_model("SilverNoticePurchaseOrderLink"),
        rows,
        MODULE.SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS,
    )

    assert deduplicated == 1
    assert dummy.execute_calls == 1


def test_silver_guardrails_reject_predictive_score_columns() -> None:
    rows = [
        {
            "notice_id": "N-1",
            "notice_status_name": "Publicada",
            "opportunity_score": 0.98,
        }
    ]
    dummy = _DummySession()

    with pytest.raises(ValueError, match="leakage guardrail violation"):
        MODULE.upsert_rows(
            dummy,
            _require_model("SilverNotice"),
            rows,
            MODULE.SILVER_NOTICE_CONFLICT_FIELDS,
        )


def test_silver_guardrails_reject_future_prefixed_columns() -> None:
    rows = [
        {
            "purchase_order_id": "OC-1",
            "purchase_order_status_name": "Aceptada",
            "future_award_outcome": "won",
        }
    ]
    dummy = _DummySession()

    with pytest.raises(ValueError, match="leakage guardrail violation"):
        MODULE.upsert_rows(
            dummy,
            _require_model("SilverPurchaseOrder"),
            rows,
            MODULE.SILVER_PURCHASE_ORDER_CONFLICT_FIELDS,
        )


def test_annotation_guardrails_reject_non_reference_tfidf_values() -> None:
    rows = [
        {
            "notice_id": "N-1",
            "nlp_version": "silver_nlp_v1",
            "corpus_scope": "notice_description",
            "tfidf_artifact_ref": "{\"vector\": [0.1, 0.2]}",
        }
    ]
    dummy = _DummySession()

    with pytest.raises(ValueError, match="annotation contract violation"):
        MODULE.upsert_rows(
            dummy,
            _require_model("SilverNoticeTextAnn"),
            rows,
            MODULE.SILVER_NOTICE_TEXT_ANN_CONFLICT_FIELDS,
        )


def test_annotation_guardrails_reject_serialized_tfidf_columns() -> None:
    rows = [
        {
            "notice_id": "N-1",
            "nlp_version": "silver_nlp_v1",
            "corpus_scope": "notice_description",
            "tfidf_artifact_ref": "tfidf://silver_notice/silver_nlp_v1/hash",
            "tfidf_vector": "[0.1, 0.2]",
        }
    ]
    dummy = _DummySession()

    with pytest.raises(ValueError, match="serialized TF-IDF vector columns are forbidden"):
        MODULE.upsert_rows(
            dummy,
            _require_model("SilverNoticeTextAnn"),
            rows,
            MODULE.SILVER_NOTICE_TEXT_ANN_CONFLICT_FIELDS,
        )


def test_refresh_silver_notice_and_line_enrichments_updates_expected_fields() -> None:
    refresh = _require_callable("refresh_silver_notice_and_line_enrichments")
    session = _RecordingSession()

    refresh(session)

    assert session.execute_calls == 2
    assert any("notice_line_count" in statement for statement in session.statements)
    assert any("notice_bid_count" in statement for statement in session.statements)
    assert any("line_bid_count" in statement for statement in session.statements)
    assert any("line_price_dispersion_ratio" in statement for statement in session.statements)


def test_refresh_silver_purchase_order_enrichments_updates_expected_fields() -> None:
    refresh = _require_callable("refresh_silver_purchase_order_enrichments")
    session = _RecordingSession()

    refresh(session)

    assert session.execute_calls == 1
    statement = session.statements[0]
    assert "purchase_order_line_count" in statement
    assert "purchase_order_total_quantity" in statement
    assert "purchase_order_total_net_amount" in statement
    assert "purchase_order_unique_product_count" in statement


def test_reconcile_notice_purchase_order_links_uses_insert_select_path() -> None:
    reconcile = _require_callable("reconcile_silver_notice_purchase_order_links")
    session = _RecordingSession()

    inserted = reconcile(session)

    assert inserted == 1
    assert session.execute_calls == 1
    statement = session.statements[0].lower()
    assert "insert into silver_notice_purchase_order_link" in statement
    assert "from silver_purchase_order" in statement
    assert "join silver_notice" in statement
    assert "on conflict" in statement


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


def test_silver_licitaciones_flush_chunk_orders_dimensions_before_facts(
    monkeypatch: Any,
) -> None:
    flush_silver_licitaciones_chunk_buffers = _require_callable(
        "flush_silver_licitaciones_chunk_buffers"
    )
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
    flush_silver_licitaciones_chunk_buffers(
        session=_DummySession(),
        chunk_size=100,
        buying_org_rows=[{"buying_org_id": "BO-1"}],
        contracting_unit_rows=[{"contracting_unit_id": "UC-1", "buying_org_id": "BO-1"}],
        supplier_rows=[{"supplier_id": "codigo:P-1"}],
        category_ref_rows=[{"category_ref_id": "cat:1"}],
        notice_rows=[{"notice_id": "N-1"}],
        notice_line_rows=[{"notice_id": "N-1", "item_code": "IT-1"}],
        bid_submission_rows=[{"bid_submission_id": "b" * 64}],
        award_outcome_rows=[{"award_outcome_id": "a" * 64}],
        supplier_participation_rows=[{"supplier_id": "codigo:P-1", "notice_id": "N-1"}],
        notice_text_ann_rows=[{"notice_id": "N-1", "nlp_version": "silver_nlp_v1"}],
        notice_line_text_ann_rows=[
            {"notice_id": "N-1", "item_code": "IT-1", "nlp_version": "silver_nlp_v1"}
        ],
    )

    assert calls == [
        "SilverBuyingOrg",
        "SilverContractingUnit",
        "SilverSupplier",
        "SilverCategoryRef",
        "SilverNotice",
        "SilverNoticeLine",
        "SilverBidSubmission",
        "SilverAwardOutcome",
        "SilverSupplierParticipation",
        "SilverNoticeTextAnn",
        "SilverNoticeLineTextAnn",
    ]


def test_silver_ordenes_flush_chunk_orders_dimensions_before_facts(
    monkeypatch: Any,
) -> None:
    flush_silver_ordenes_chunk_buffers = _require_callable("flush_silver_ordenes_chunk_buffers")
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
    flush_silver_ordenes_chunk_buffers(
        session=_DummySession(),
        chunk_size=100,
        buying_org_rows=[{"buying_org_id": "BO-1"}],
        contracting_unit_rows=[{"contracting_unit_id": "UC-1", "buying_org_id": "BO-1"}],
        supplier_rows=[{"supplier_id": "codigo:P-1"}],
        category_ref_rows=[{"category_ref_id": "cat:1"}],
        purchase_order_rows=[{"purchase_order_id": "OC-1"}],
        purchase_order_line_rows=[{"purchase_order_id": "OC-1", "line_item_id": "1"}],
        notice_purchase_order_link_rows=[
            {"notice_id": "N-1", "purchase_order_id": "OC-1", "link_type": "explicit_code_match"}
        ],
        purchase_order_line_text_ann_rows=[
            {"purchase_order_id": "OC-1", "line_item_id": "1", "nlp_version": "silver_nlp_v1"}
        ],
    )

    assert calls == [
        "SilverBuyingOrg",
        "SilverContractingUnit",
        "SilverSupplier",
        "SilverCategoryRef",
        "SilverPurchaseOrder",
        "SilverPurchaseOrderLine",
        "SilverNoticePurchaseOrderLink",
        "SilverPurchaseOrderLineTextAnn",
    ]


def test_silver_ordenes_flush_chunk_forces_dimension_flush_when_facts_reach_chunk(
    monkeypatch: Any,
) -> None:
    flush_silver_ordenes_chunk_buffers = _require_callable("flush_silver_ordenes_chunk_buffers")
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
    flush_silver_ordenes_chunk_buffers(
        session=_DummySession(),
        chunk_size=2,
        buying_org_rows=[{"buying_org_id": "BO-1"}],
        contracting_unit_rows=[{"contracting_unit_id": "UC-1", "buying_org_id": "BO-1"}],
        supplier_rows=[{"supplier_id": "codigo:P-1"}],
        category_ref_rows=[{"category_ref_id": "cat:1"}],
        purchase_order_rows=[{"purchase_order_id": "OC-1"}, {"purchase_order_id": "OC-2"}],
        purchase_order_line_rows=[],
        notice_purchase_order_link_rows=[],
        purchase_order_line_text_ann_rows=[],
    )

    assert forced_by_model["SilverBuyingOrg"] is True
    assert forced_by_model["SilverContractingUnit"] is True
    assert forced_by_model["SilverSupplier"] is True
    assert forced_by_model["SilverCategoryRef"] is True
    assert forced_by_model["SilverPurchaseOrder"] is True
    assert forced_by_model["SilverPurchaseOrderLine"] is False


def test_silver_ordenes_flush_chunk_forces_purchase_order_parent_when_links_reach_chunk(
    monkeypatch: Any,
) -> None:
    flush_silver_ordenes_chunk_buffers = _require_callable("flush_silver_ordenes_chunk_buffers")
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
    flush_silver_ordenes_chunk_buffers(
        session=_DummySession(),
        chunk_size=2,
        buying_org_rows=[],
        contracting_unit_rows=[],
        supplier_rows=[],
        category_ref_rows=[],
        purchase_order_rows=[{"purchase_order_id": "OC-1"}],
        purchase_order_line_rows=[],
        notice_purchase_order_link_rows=[
            {"notice_id": "N-1", "purchase_order_id": "OC-1", "link_type": "explicit_code_match"},
            {"notice_id": "N-2", "purchase_order_id": "OC-1", "link_type": "explicit_code_match"},
        ],
        purchase_order_line_text_ann_rows=[],
    )

    assert forced_by_model["SilverPurchaseOrder"] is True
    assert forced_by_model["SilverPurchaseOrderLine"] is False


def test_silver_ordenes_flush_chunk_forces_purchase_order_line_parent_for_text_ann(
    monkeypatch: Any,
) -> None:
    flush_silver_ordenes_chunk_buffers = _require_callable("flush_silver_ordenes_chunk_buffers")
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
    flush_silver_ordenes_chunk_buffers(
        session=_DummySession(),
        chunk_size=2,
        buying_org_rows=[],
        contracting_unit_rows=[],
        supplier_rows=[],
        category_ref_rows=[],
        purchase_order_rows=[{"purchase_order_id": "OC-1"}],
        purchase_order_line_rows=[{"purchase_order_id": "OC-1", "line_item_id": "1"}],
        notice_purchase_order_link_rows=[],
        purchase_order_line_text_ann_rows=[
            {"purchase_order_id": "OC-1", "line_item_id": "1", "nlp_version": "silver_nlp_v1"},
            {"purchase_order_id": "OC-1", "line_item_id": "2", "nlp_version": "silver_nlp_v1"},
        ],
    )

    assert forced_by_model["SilverPurchaseOrder"] is True
    assert forced_by_model["SilverPurchaseOrderLine"] is True


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
