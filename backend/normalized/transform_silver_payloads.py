from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.normalized.transform_common import (
    award_outcome_key_from_raw,
    has_bid_submission_signal,
    oferta_key_from_raw,
    parse_bool,
    parse_bool_or_false,
    parse_datetime,
    parse_decimal,
    parse_int,
    pick,
)
from backend.normalized.transform_identity import (
    resolve_buying_org_identity_key,
    resolve_category_ref_identity_key,
    resolve_contracting_unit_identity_key,
    resolve_supplier_identity_key,
)
from backend.pipeline.shared.cleaning import normalize_text_base


def build_silver_notice_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    notice_id = pick(raw, "CodigoExterno")
    if notice_id is None:
        return None

    publication_date = parse_datetime(pick(raw, "FechaPublicacion"))
    created_date = parse_datetime(pick(raw, "FechaCreacion"))
    close_date = parse_datetime(pick(raw, "FechaCierre"))
    award_date = parse_datetime(pick(raw, "FechaAdjudicacion"))
    procurement_method_name = pick(raw, "Tipo de Adquisicion")
    procurement_method_norm = normalize_text_base(procurement_method_name) or ""
    visibility_norm = normalize_text_base(pick(raw, "VisibilidadMonto")) or ""
    etapas = parse_int(pick(raw, "Etapas"))

    days_publication_to_close = None
    if publication_date is not None and close_date is not None:
        days_publication_to_close = (close_date - publication_date).days

    days_creation_to_close = None
    if created_date is not None and close_date is not None:
        days_creation_to_close = (close_date - created_date).days

    days_close_to_award = None
    if close_date is not None and award_date is not None:
        days_close_to_award = (award_date - close_date).days

    return {
        "notice_id": notice_id,
        "external_notice_code": notice_id,
        "notice_url": pick(raw, "Link"),
        "notice_title": pick(raw, "Nombre"),
        "notice_description_raw": pick(raw, "Descripcion"),
        "notice_description_clean": normalize_text_base(pick(raw, "Descripcion")),
        "procurement_method_name": procurement_method_name,
        "procurement_method_code": pick(raw, "CodigoTipo"),
        "notice_status_name": pick(raw, "Estado"),
        "notice_status_code": pick(raw, "CodigoEstado"),
        "publication_date": publication_date,
        "created_date": created_date,
        "close_date": close_date,
        "award_date": award_date,
        "estimated_award_date": parse_datetime(pick(raw, "FechaEstimadaAdjudicacion")),
        "estimated_amount": parse_decimal(pick(raw, "MontoEstimado")),
        "currency_code": pick(raw, "CodigoMoneda"),
        "currency_name": pick(raw, "Moneda Adquisicion"),
        "number_of_bidders_reported": parse_int(pick(raw, "NumeroOferentes")),
        "complaint_count": parse_int(pick(raw, "CantidadReclamos")),
        "days_publication_to_close": days_publication_to_close,
        "days_creation_to_close": days_creation_to_close,
        "days_close_to_award": days_close_to_award,
        "has_missing_date_chain_flag": (
            publication_date is None or close_date is None or award_date is None
        ),
        "is_public_tender_flag": "licitacion publica" in procurement_method_norm,
        "is_private_tender_flag": "licitacion privada" in procurement_method_norm,
        "requires_toma_razon_flag": parse_bool_or_false(pick(raw, "TomaRazon")),
        "multiple_stages_flag": bool((etapas or 0) > 1),
        "hidden_budget_flag": visibility_norm in {"0", "no", "oculto", "reservado"},
        "has_extension_flag": parse_bool_or_false(pick(raw, "ExtensionPlazo")),
        "has_site_visit_flag": parse_datetime(pick(raw, "FechaVisitaTerreno")) is not None,
        "has_physical_document_delivery_flag": (
            parse_datetime(pick(raw, "FechaEntregaAntecedentes")) is not None
            or parse_datetime(pick(raw, "FechaSoporteFisico")) is not None
        ),
        "notice_line_count": 0,
        "notice_bid_count": 0,
        "notice_supplier_count": 0,
        "notice_selected_bid_count": 0,
        "notice_awarded_line_count": 0,
        "notice_has_purchase_order_flag": False,
        "notice_purchase_order_count": 0,
        "notice_awarded_to_order_conversion_flag": False,
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_notice_line_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    notice_id = pick(raw, "CodigoExterno")
    item_code = pick(raw, "Codigoitem", "CodigoItem")
    if notice_id is None or item_code is None:
        return None

    return {
        "notice_id": notice_id,
        "line_number": pick(raw, "Correlativo"),
        "item_code": item_code,
        "onu_product_code": pick(raw, "CodigoProductoONU"),
        "category_level_1": pick(raw, "Rubro1"),
        "category_level_2": pick(raw, "Rubro2"),
        "category_level_3": pick(raw, "Rubro3"),
        "generic_product_name": pick(raw, "Nombre producto genrico"),
        "line_name": pick(raw, "Nombre linea Adquisicion"),
        "line_description_raw": pick(raw, "Descripcion linea Adquisicion"),
        "line_description_clean": normalize_text_base(pick(raw, "Descripcion linea Adquisicion")),
        "unit_of_measure": pick(raw, "UnidadMedida"),
        "quantity_requested": parse_decimal(pick(raw, "Cantidad")),
        "line_bid_count": 0,
        "line_supplier_count": 0,
        "line_min_offer_amount": None,
        "line_max_offer_amount": None,
        "line_avg_offer_amount": None,
        "line_median_offer_amount": None,
        "line_price_dispersion_ratio": None,
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_bid_submission_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    notice_id = pick(raw, "CodigoExterno")
    if notice_id is None:
        return None

    supplier_id = resolve_supplier_identity_key(raw)
    if supplier_id is None:
        return None

    offer_signal = has_bid_submission_signal(raw)
    if not offer_signal:
        return None

    return {
        "bid_submission_id": oferta_key_from_raw(raw),
        "notice_id": notice_id,
        "notice_line_id": None,
        "item_code": pick(raw, "Codigoitem", "CodigoItem"),
        "supplier_key": supplier_id,
        "supplier_branch_id": pick(raw, "CodigoSucursalProveedor"),
        "offer_name": pick(raw, "Nombre de la Oferta"),
        "offer_status": pick(raw, "Estado Oferta"),
        "offer_submission_date": parse_datetime(pick(raw, "FechaEnvioOferta")),
        "offered_quantity": parse_decimal(pick(raw, "Cantidad Ofertada")),
        "offer_currency_name": pick(raw, "Moneda de la Oferta"),
        "unit_price_offered": parse_decimal(pick(raw, "MontoUnitarioOferta")),
        "total_price_offered": parse_decimal(pick(raw, "Valor Total Ofertado")),
        "selected_offer_flag": parse_bool(pick(raw, "Oferta seleccionada")),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_award_outcome_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    notice_id = pick(raw, "CodigoExterno")
    supplier_id = resolve_supplier_identity_key(raw)
    if notice_id is None or supplier_id is None:
        return None

    selected_offer_flag = parse_bool(pick(raw, "Oferta seleccionada"))
    awarded_quantity = parse_decimal(pick(raw, "CantidadAdjudicada"))
    awarded_line_amount = parse_decimal(pick(raw, "MontoLineaAdjudica"))
    has_award_signal = (
        selected_offer_flag is not None
        or awarded_quantity is not None
        or awarded_line_amount is not None
    )
    if not has_award_signal:
        return None

    bid_submission_id = oferta_key_from_raw(raw) if has_bid_submission_signal(raw) else None

    return {
        "award_outcome_id": award_outcome_key_from_raw(raw),
        "bid_submission_id": bid_submission_id,
        "notice_id": notice_id,
        "notice_line_id": None,
        "item_code": pick(raw, "Codigoitem", "CodigoItem"),
        "supplier_key": supplier_id,
        "selected_offer_flag": selected_offer_flag,
        "awarded_quantity": awarded_quantity,
        "awarded_line_amount": awarded_line_amount,
        "award_date": parse_datetime(pick(raw, "FechaAdjudicacion")),
        "award_status": pick(raw, "Estado"),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_purchase_order_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    purchase_order_id = pick(raw, "Codigo")
    if purchase_order_id is None:
        return None

    order_created_at = parse_datetime(pick(raw, "FechaCreacion"))
    order_accepted_at = parse_datetime(pick(raw, "FechaAceptacion"))
    order_cancelled_at = parse_datetime(pick(raw, "FechaCancelacion"))
    linked_notice_id = pick(raw, "CodigoLicitacion")

    days_order_creation_to_acceptance = None
    if order_created_at is not None and order_accepted_at is not None:
        days_order_creation_to_acceptance = (order_accepted_at - order_created_at).days

    days_order_creation_to_cancellation = None
    if order_created_at is not None and order_cancelled_at is not None:
        days_order_creation_to_cancellation = (order_cancelled_at - order_created_at).days

    return {
        "purchase_order_id": purchase_order_id,
        "purchase_order_code": pick(raw, "ID"),
        "purchase_order_url": pick(raw, "Link"),
        "purchase_order_name": pick(raw, "Nombre"),
        "purchase_order_description_raw": pick(raw, "Descripcion/Obervaciones"),
        "purchase_order_description_clean": normalize_text_base(pick(raw, "Descripcion/Obervaciones")),
        "purchase_order_type": pick(raw, "Tipo"),
        "purchase_order_type_code": pick(raw, "CodigoTipo"),
        "purchase_order_status_code": pick(raw, "codigoEstado"),
        "purchase_order_status_name": pick(raw, "Estado"),
        "supplier_status_code": pick(raw, "codigoEstadoProveedor"),
        "supplier_status_name": pick(raw, "EstadoProveedor"),
        "order_created_at": order_created_at,
        "order_sent_at": parse_datetime(pick(raw, "FechaEnvio")),
        "order_accepted_at": order_accepted_at,
        "order_cancelled_at": order_cancelled_at,
        "order_last_modified_at": parse_datetime(pick(raw, "fechaUltimaModificacion")),
        "days_order_creation_to_acceptance": days_order_creation_to_acceptance,
        "days_order_creation_to_cancellation": days_order_creation_to_cancellation,
        "total_amount": parse_decimal(pick(raw, "MontoTotalOC")),
        "net_total_amount": parse_decimal(pick(raw, "TotalNetoOC")),
        "tax_amount": parse_decimal(pick(raw, "Impuestos")),
        "discount_amount": parse_decimal(pick(raw, "Descuentos")),
        "charge_amount": parse_decimal(pick(raw, "Cargos")),
        "currency_code": pick(raw, "TipoMonedaOC"),
        "currency_name": pick(raw, "TipoMonedaOC"),
        "supplier_key": resolve_supplier_identity_key(raw),
        "supplier_branch_id": pick(raw, "CodigoSucursal"),
        "linked_notice_id": linked_notice_id,
        "is_linked_to_notice_flag": linked_notice_id is not None,
        "is_direct_award_flag": parse_bool_or_false(pick(raw, "EsTratoDirecto")),
        "is_agile_purchase_flag": parse_bool_or_false(pick(raw, "EsCompraAgil")),
        "has_items_flag": parse_bool_or_false(pick(raw, "tieneItems")),
        "purchase_order_line_count": 0,
        "purchase_order_total_quantity": None,
        "purchase_order_total_net_amount": None,
        "purchase_order_unique_product_count": 0,
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_purchase_order_line_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    purchase_order_id = pick(raw, "Codigo")
    line_item_id = pick(raw, "IDItem")
    if purchase_order_id is None or line_item_id is None:
        return None

    return {
        "purchase_order_id": purchase_order_id,
        "line_item_id": line_item_id,
        "linked_notice_id": pick(raw, "CodigoLicitacion"),
        "onu_product_code": pick(raw, "codigoProductoONU"),
        "category_code": pick(raw, "codigoCategoria"),
        "category_name": pick(raw, "Categoria"),
        "category_level_1": pick(raw, "RubroN1"),
        "category_level_2": pick(raw, "RubroN2"),
        "category_level_3": pick(raw, "RubroN3"),
        "generic_product_name": pick(raw, "NombreroductoGenerico", "NombreProductoGenerico"),
        "buyer_item_spec_raw": pick(raw, "EspecificacionComprador"),
        "buyer_item_spec_clean": normalize_text_base(pick(raw, "EspecificacionComprador")),
        "supplier_item_spec_raw": pick(raw, "EspecificacionProveedor"),
        "supplier_item_spec_clean": normalize_text_base(pick(raw, "EspecificacionProveedor")),
        "quantity_ordered": parse_decimal(pick(raw, "cantidad")),
        "unit_of_measure": pick(raw, "UnidadMedida"),
        "line_currency": pick(raw, "monedaItem"),
        "unit_net_price": parse_decimal(pick(raw, "precioNeto")),
        "line_net_total": parse_decimal(pick(raw, "totalLineaNeto")),
        "line_tax_total": parse_decimal(pick(raw, "totalImpuestos")),
        "line_discount_total": parse_decimal(pick(raw, "totalDescuentos")),
        "line_charge_total": parse_decimal(pick(raw, "totalCargos")),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_buying_org_payload(
    raw: dict[str, Any],
    source_file_id: Any,
) -> dict[str, Any] | None:
    buying_org_id = resolve_buying_org_identity_key(raw)
    if buying_org_id is None:
        return None

    return {
        "buying_org_id": buying_org_id,
        "buying_org_name": pick(raw, "OrganismoPublico", "NombreOrganismo"),
        "sector_name": pick(raw, "sector"),
        "source_file_id": source_file_id,
    }


def build_silver_contracting_unit_payload(
    raw: dict[str, Any],
    source_file_id: Any,
) -> dict[str, Any] | None:
    contracting_unit_id = resolve_contracting_unit_identity_key(raw)
    buying_org_id = resolve_buying_org_identity_key(raw)
    if contracting_unit_id is None or buying_org_id is None:
        return None

    return {
        "contracting_unit_id": contracting_unit_id,
        "buying_org_id": buying_org_id,
        "unit_rut": pick(raw, "RutUnidadCompra", "RutUnidad"),
        "unit_name": pick(raw, "UnidadCompra", "NombreUnidad"),
        "unit_address": pick(raw, "DireccionUnidad"),
        "unit_commune": pick(raw, "ComunaUnidad"),
        "unit_region": pick(raw, "RegionUnidad", "RegionUnidadCompra"),
        "unit_city": pick(raw, "CiudadUnidadCompra"),
        "unit_country": pick(raw, "PaisUnidadCompra"),
        "source_file_id": source_file_id,
    }


def build_silver_supplier_payload(
    raw: dict[str, Any],
    source_file_id: Any,
) -> dict[str, Any] | None:
    supplier_id = resolve_supplier_identity_key(raw)
    if supplier_id is None:
        return None

    return {
        "supplier_id": supplier_id,
        "supplier_branch_id": pick(raw, "CodigoSucursalProveedor", "CodigoSucursal"),
        "supplier_rut": pick(raw, "RutProveedor"),
        "supplier_trade_name": pick(raw, "NombreProveedor"),
        "supplier_legal_name": pick(raw, "RazonSocialProveedor"),
        "supplier_activity": pick(raw, "ActividadProveedor"),
        "supplier_commune": pick(raw, "ComunaProveedor"),
        "supplier_region": pick(raw, "RegionProveedor"),
        "supplier_country": pick(raw, "PaisProveedor"),
        "source_file_id": source_file_id,
    }


def build_silver_category_ref_payload(
    raw: dict[str, Any],
    source_file_id: Any,
) -> dict[str, Any] | None:
    category_ref_id = resolve_category_ref_identity_key(raw)
    if category_ref_id is None:
        return None

    return {
        "category_ref_id": category_ref_id,
        "onu_product_code": pick(raw, "codigoProductoONU", "CodigoProductoONU"),
        "category_code": pick(raw, "codigoCategoria"),
        "category_name": pick(raw, "Categoria"),
        "category_level_1": pick(raw, "RubroN1", "Rubro1"),
        "category_level_2": pick(raw, "RubroN2", "Rubro2"),
        "category_level_3": pick(raw, "RubroN3", "Rubro3"),
        "generic_product_name_canonical": pick(
            raw,
            "NombreroductoGenerico",
            "NombreProductoGenerico",
            "Nombre producto genrico",
        ),
        "source_file_id": source_file_id,
    }


def build_silver_notice_purchase_order_link_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    purchase_order_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if purchase_order_payload is None:
        return None

    linked_notice_id = pick(raw, "CodigoLicitacion")
    if linked_notice_id is None:
        return None

    purchase_order_id = purchase_order_payload.get("purchase_order_id")
    if not isinstance(purchase_order_id, str) or purchase_order_id.strip() == "":
        return None

    return {
        "notice_id": linked_notice_id,
        "purchase_order_id": purchase_order_id,
        "link_type": "explicit_code_match",
        "link_confidence": Decimal("1"),
        "source_system": "mercado_publico_csv",
        "source_file_id": source_file_id,
    }


def build_silver_supplier_participation_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    bid_submission_payload: dict[str, Any] | None,
    award_outcome_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    supplier_id = resolve_supplier_identity_key(raw)
    notice_id = pick(raw, "CodigoExterno", "CodigoLicitacion")
    if supplier_id is None or notice_id is None:
        return None

    bid_submission_id = None
    if bid_submission_payload is not None:
        bid_submission_id = bid_submission_payload.get("bid_submission_id")

    award_outcome_id = None
    if award_outcome_payload is not None:
        award_outcome_id = award_outcome_payload.get("award_outcome_id")

    selected_offer = parse_bool(pick(raw, "Oferta seleccionada"))
    was_selected = bool(selected_offer is True or award_outcome_payload is not None)
    was_materialized = pick(raw, "CodigoLicitacion") is not None

    return {
        "supplier_id": supplier_id,
        "notice_id": notice_id,
        "notice_line_id": None,
        "bid_submission_id": bid_submission_id,
        "award_outcome_id": award_outcome_id,
        "purchase_order_line_id": None,
        "was_selected_flag": was_selected,
        "was_materialized_in_purchase_order_flag": was_materialized,
        "source_file_id": source_file_id,
    }
