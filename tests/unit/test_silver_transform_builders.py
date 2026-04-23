from __future__ import annotations

from uuid import uuid4

from backend.normalized.transform import (
    build_silver_award_outcome_payload,
    build_silver_bid_submission_payload,
    build_silver_buying_org_payload,
    build_silver_category_ref_payload,
    build_silver_contracting_unit_payload,
    build_silver_notice_line_payload,
    build_silver_notice_line_text_ann_payload,
    build_silver_notice_payload,
    build_silver_notice_text_ann_payload,
    build_silver_notice_purchase_order_link_payload,
    build_silver_purchase_order_line_payload,
    build_silver_purchase_order_line_text_ann_payload,
    build_silver_purchase_order_payload,
    build_silver_supplier_participation_payload,
    build_silver_supplier_payload,
    resolve_buying_org_identity_key,
    resolve_category_ref_identity_key,
    resolve_contracting_unit_identity_key,
)


def test_silver_identity_resolvers_precedence() -> None:
    assert resolve_buying_org_identity_key({"CodigoOrganismoPublico": "BO-1"}) == "BO-1"
    assert resolve_buying_org_identity_key({"CodigoOrganismo": "ORG-1"}) == "ORG-1"

    assert resolve_contracting_unit_identity_key({"CodigoUnidadCompra": "UC-9"}) == "UC-9"
    assert resolve_contracting_unit_identity_key({"CodigoUnidad": "U-9"}) == "U-9"

    assert resolve_category_ref_identity_key({"codigoCategoria": "300000"}) == "cat:300000"
    assert resolve_category_ref_identity_key({"CodigoProductoONU": "72131702"}) == "onu:72131702"


def test_build_silver_notice_payload_requires_notice_id() -> None:
    payload = build_silver_notice_payload({}, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is None


def test_build_silver_notice_payload_maps_core_fields() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "Nombre": "Aviso",
        "Descripcion": "Compra de guantes",
        "Tipo de Adquisicion": "Licitacion Publica",
        "CodigoEstado": "6",
        "Estado": "Cerrada",
        "FechaPublicacion": "2026-01-01",
        "FechaCierre": "2026-01-10",
        "MontoEstimado": "1234,56",
        "NumeroOferentes": "3",
    }
    payload = build_silver_notice_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["notice_id"] == "N-1"
    assert payload["notice_status_name"] == "Cerrada"
    assert str(payload["estimated_amount"]) == "1234.56"
    assert payload["number_of_bidders_reported"] == 3


def test_build_silver_notice_payload_derives_temporal_and_admin_flags() -> None:
    raw = {
        "CodigoExterno": "N-2",
        "Tipo de Adquisicion": "Licitacion Publica",
        "FechaPublicacion": "2026-01-01",
        "FechaCreacion": "2025-12-30",
        "FechaCierre": "2026-01-11",
        "FechaAdjudicacion": "2026-01-20",
        "TomaRazon": "Si",
        "Etapas": "2",
        "VisibilidadMonto": "No",
        "ExtensionPlazo": "Si",
        "FechaVisitaTerreno": "2026-01-02",
    }
    payload = build_silver_notice_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["days_publication_to_close"] == 10
    assert payload["days_creation_to_close"] == 12
    assert payload["days_close_to_award"] == 9
    assert payload["has_missing_date_chain_flag"] is False
    assert payload["is_public_tender_flag"] is True
    assert payload["requires_toma_razon_flag"] is True
    assert payload["multiple_stages_flag"] is True
    assert payload["hidden_budget_flag"] is True
    assert payload["has_extension_flag"] is True
    assert payload["has_site_visit_flag"] is True


def test_build_silver_notice_payload_defaults_non_nullable_flags_to_false() -> None:
    payload = build_silver_notice_payload(
        {"CodigoExterno": "N-3"},
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is not None
    assert payload["requires_toma_razon_flag"] is False
    assert payload["has_extension_flag"] is False


def test_build_silver_notice_line_payload_requires_notice_and_item() -> None:
    payload = build_silver_notice_line_payload(
        {"CodigoExterno": "N-1"}, source_file_id=uuid4(), row_hash_sha256="h" * 64
    )
    assert payload is None


def test_build_silver_notice_line_payload_maps_fields() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "Codigoitem": "IT-1",
        "Rubro1": "A",
        "Descripcion linea Adquisicion": "Linea",
    }
    payload = build_silver_notice_line_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["notice_id"] == "N-1"
    assert payload["item_code"] == "IT-1"
    assert payload["category_level_1"] == "A"


def test_build_silver_bid_submission_payload_requires_supplier_and_offer_signal() -> None:
    raw = {"CodigoExterno": "N-1", "Nombre de la Oferta": "X"}
    payload = build_silver_bid_submission_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is None


def test_build_silver_bid_submission_payload_maps_offer() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "CodigoProveedor": "P-1",
        "Nombre de la Oferta": "Oferta A",
        "Estado Oferta": "Aceptada",
        "MontoUnitarioOferta": "1000",
    }
    payload = build_silver_bid_submission_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["notice_id"] == "N-1"
    assert payload["supplier_key"] == "codigo:P-1"
    assert payload["offer_name"] == "Oferta A"


def test_build_silver_award_outcome_payload_requires_award_signal() -> None:
    raw = {"CodigoExterno": "N-1", "CodigoProveedor": "P-1"}
    payload = build_silver_award_outcome_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is None


def test_build_silver_award_outcome_payload_maps_award() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "CodigoProveedor": "P-1",
        "Oferta seleccionada": "Seleccionada",
        "CantidadAdjudicada": "2",
    }
    payload = build_silver_award_outcome_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["notice_id"] == "N-1"
    assert payload["supplier_key"] == "codigo:P-1"
    assert payload["selected_offer_flag"] is True
    assert payload["bid_submission_id"] is None


def test_build_silver_award_outcome_payload_sets_bid_submission_fk_with_offer_signal() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "CodigoProveedor": "P-1",
        "Estado Oferta": "Aceptada",
        "CantidadAdjudicada": "2",
    }
    payload = build_silver_award_outcome_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["bid_submission_id"] is not None


def test_build_silver_purchase_order_payload_requires_code() -> None:
    payload = build_silver_purchase_order_payload({}, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is None


def test_build_silver_purchase_order_payload_maps_order() -> None:
    raw = {
        "Codigo": "OC-1",
        "ID": "123",
        "Estado": "Aceptada",
        "CodigoProveedor": "P-1",
        "CodigoLicitacion": "N-1",
        "tieneItems": "1",
    }
    payload = build_silver_purchase_order_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["purchase_order_id"] == "OC-1"
    assert payload["supplier_key"] == "codigo:P-1"
    assert payload["linked_notice_id"] == "N-1"
    assert payload["has_items_flag"] is True


def test_build_silver_purchase_order_payload_derives_temporal_and_aggregate_defaults() -> None:
    raw = {
        "Codigo": "OC-2",
        "FechaCreacion": "2026-01-01",
        "FechaAceptacion": "2026-01-05",
        "FechaCancelacion": "2026-01-10",
        "CodigoLicitacion": "N-99",
    }
    payload = build_silver_purchase_order_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["days_order_creation_to_acceptance"] == 4
    assert payload["days_order_creation_to_cancellation"] == 9
    assert payload["is_linked_to_notice_flag"] is True
    assert payload["purchase_order_line_count"] == 0
    assert payload["purchase_order_unique_product_count"] == 0


def test_build_silver_purchase_order_payload_defaults_non_nullable_flags_to_false() -> None:
    payload = build_silver_purchase_order_payload(
        {"Codigo": "OC-3"},
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is not None
    assert payload["is_direct_award_flag"] is False
    assert payload["is_agile_purchase_flag"] is False
    assert payload["has_items_flag"] is False


def test_build_silver_purchase_order_line_payload_requires_keys() -> None:
    payload = build_silver_purchase_order_line_payload(
        {"Codigo": "OC-1"}, source_file_id=uuid4(), row_hash_sha256="h" * 64
    )
    assert payload is None


def test_build_silver_purchase_order_line_payload_maps_line() -> None:
    raw = {"Codigo": "OC-1", "IDItem": "1", "precioNeto": "500"}
    payload = build_silver_purchase_order_line_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert payload is not None
    assert payload["purchase_order_id"] == "OC-1"
    assert payload["line_item_id"] == "1"
    assert str(payload["unit_net_price"]) == "500"


def test_build_silver_notice_text_ann_payload_requires_notice_id() -> None:
    payload = build_silver_notice_text_ann_payload(
        raw={},
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is None


def test_build_silver_notice_text_ann_payload_maps_annotation_contract() -> None:
    payload = build_silver_notice_text_ann_payload(
        raw={"CodigoExterno": "N-1", "Descripcion": "Servicio de mantencion y soporte de software"},
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is not None
    assert payload["notice_id"] == "N-1"
    assert payload["nlp_version"] == "silver_nlp_v1"
    assert payload["corpus_scope"] == "notice_description"
    assert isinstance(payload["normalized_tokens_json"], list)
    assert payload["tfidf_artifact_ref"].startswith("tfidf://silver_notice/")


def test_build_silver_notice_line_text_ann_payload_requires_notice_line_keys() -> None:
    payload = build_silver_notice_line_text_ann_payload(
        raw={"CodigoExterno": "N-1"},
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is None


def test_build_silver_notice_line_text_ann_payload_maps_annotation_contract() -> None:
    payload = build_silver_notice_line_text_ann_payload(
        raw={
            "CodigoExterno": "N-1",
            "Codigoitem": "IT-1",
            "Descripcion linea Adquisicion": "Licencias de software y soporte tecnico",
        },
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is not None
    assert payload["notice_id"] == "N-1"
    assert payload["item_code"] == "IT-1"
    assert payload["nlp_version"] == "silver_nlp_v1"
    assert payload["tfidf_artifact_ref"].startswith("tfidf://silver_notice_line/")


def test_build_silver_purchase_order_line_text_ann_payload_requires_keys() -> None:
    payload = build_silver_purchase_order_line_text_ann_payload(
        raw={"Codigo": "OC-1"},
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is None


def test_build_silver_purchase_order_line_text_ann_payload_maps_annotation_contract() -> None:
    payload = build_silver_purchase_order_line_text_ann_payload(
        raw={
            "Codigo": "OC-1",
            "IDItem": "1",
            "EspecificacionComprador": "Mantencion de red y soporte tecnico",
            "EspecificacionProveedor": "Servicio de soporte y monitoreo",
        },
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert payload is not None
    assert payload["purchase_order_id"] == "OC-1"
    assert payload["line_item_id"] == "1"
    assert payload["nlp_version"] == "silver_nlp_v1"
    assert isinstance(payload["buyer_spec_tags_json"], dict)
    assert isinstance(payload["supplier_spec_tags_json"], dict)
    assert payload["tfidf_artifact_ref"].startswith("tfidf://silver_purchase_order_line/")


def test_build_silver_master_payloads_require_identity() -> None:
    assert build_silver_buying_org_payload({}, source_file_id=uuid4()) is None
    assert build_silver_contracting_unit_payload({}, source_file_id=uuid4()) is None
    assert build_silver_supplier_payload({}, source_file_id=uuid4()) is None
    assert build_silver_category_ref_payload({}, source_file_id=uuid4()) is None


def test_build_silver_master_payloads_map_fields() -> None:
    raw = {
        "CodigoOrganismoPublico": "BO-1",
        "CodigoUnidadCompra": "UC-1",
        "CodigoProveedor": "P-1",
        "codigoCategoria": "300000",
        "OrganismoPublico": "Org",
    }
    buying_org = build_silver_buying_org_payload(raw, source_file_id=uuid4())
    unit = build_silver_contracting_unit_payload(raw, source_file_id=uuid4())
    supplier = build_silver_supplier_payload(raw, source_file_id=uuid4())
    category = build_silver_category_ref_payload(raw, source_file_id=uuid4())
    assert buying_org is not None and buying_org["buying_org_id"] == "BO-1"
    assert unit is not None and unit["contracting_unit_id"] == "UC-1"
    assert supplier is not None and supplier["supplier_id"] == "codigo:P-1"
    assert category is not None and category["category_ref_id"] == "cat:300000"


def test_build_notice_purchase_order_link_requires_notice_and_order() -> None:
    raw = {"CodigoLicitacion": "N-1"}
    assert (
        build_silver_notice_purchase_order_link_payload(
            raw=raw,
            source_file_id=uuid4(),
            purchase_order_payload=None,
        )
        is None
    )


def test_build_notice_purchase_order_link_maps_explicit_match() -> None:
    raw = {"CodigoLicitacion": "N-1"}
    payload = build_silver_notice_purchase_order_link_payload(
        raw=raw,
        source_file_id=uuid4(),
        purchase_order_payload={"purchase_order_id": "OC-1"},
    )
    assert payload is not None
    assert payload["notice_id"] == "N-1"
    assert payload["purchase_order_id"] == "OC-1"
    assert str(payload["link_confidence"]) == "1"


def test_build_supplier_participation_payload_requires_supplier_and_notice() -> None:
    assert (
        build_silver_supplier_participation_payload(
            raw={},
            source_file_id=uuid4(),
            bid_submission_payload=None,
            award_outcome_payload=None,
        )
        is None
    )


def test_build_supplier_participation_payload_maps_flags() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "CodigoProveedor": "P-1",
        "Oferta seleccionada": "Seleccionada",
        "CodigoLicitacion": "N-1",
    }
    payload = build_silver_supplier_participation_payload(
        raw=raw,
        source_file_id=uuid4(),
        bid_submission_payload={"bid_submission_id": "B-1"},
        award_outcome_payload={"award_outcome_id": "A-1"},
    )
    assert payload is not None
    assert payload["supplier_id"] == "codigo:P-1"
    assert payload["notice_id"] == "N-1"
    assert payload["was_selected_flag"] is True
    assert payload["was_materialized_in_purchase_order_flag"] is True
