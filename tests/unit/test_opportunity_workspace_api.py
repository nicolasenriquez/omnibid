from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from backend.api.routers.opportunities import (
    DETAIL_SQL,
    LIST_SQL,
    SUMMARY_SQL,
    get_opportunities_summary,
    get_opportunity_detail,
    list_opportunities,
)


class _ScalarResult:
    def __init__(self, row: tuple[Any, ...]) -> None:
        self._row = row

    def one(self) -> tuple[Any, ...]:
        return self._row


class _MappingResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_MappingResult":
        return self

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._rows)

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _DummySession:
    def __init__(self, responses: list[_ScalarResult | _MappingResult]) -> None:
        self._responses = responses
        self.params: list[dict[str, Any]] = []

    def execute(
        self,
        _stmt: object,
        params: dict[str, Any] | None = None,
    ) -> _ScalarResult | _MappingResult:
        if not self._responses:
            raise AssertionError("no dummy response available")
        self.params.append(params or {})
        return self._responses.pop(0)


def _list_opportunities(session: _DummySession, **overrides: Any) -> dict[str, Any]:
    params = {
        "page": 1,
        "page_size": 20,
        "sort_by": "close_date",
        "sort_order": "asc",
        "q": None,
        "official_status": None,
        "buyer_region": None,
        "primary_category": None,
        "publication_from": None,
        "publication_to": None,
        "close_from": None,
        "close_to": None,
        "min_amount": None,
        "max_amount": None,
        "procurement_type": None,
        "less_than_100_utm": None,
        "stage": None,
        "source_view": None,
        "db": session,
    }
    params.update(overrides)
    return list_opportunities(**params)  # type: ignore[arg-type]


def test_list_opportunities_serializes_dates_and_decimals() -> None:
    session = _DummySession(
        [
            _ScalarResult((1,)),
            _MappingResult(
                [
                    {
                        "notice_id": "123-1-LP26",
                        "external_notice_code": "123-1-LP26",
                        "title": "Compra de servicios",
                        "notice_description_raw": "Detalle de servicios",
                        "official_status": "Publicada",
                        "mp_estado_codigo": 5,
                        "mp_estado_nombre": "Publicada",
                        "mp_estado_canonical": "publicada",
                        "data_source_kind": "api_publicada",
                        "availability_context": "current_publicada_discovery",
                        "codigo_tipo": "L1",
                        "tipo": "Licitacion Publica",
                        "tipo_convocatoria": "1",
                        "informada": "No",
                        "visibilidad_monto": "Visible",
                        "fuente_financiamiento": "Municipal",
                        "complaint_count": 3,
                        "estimated_amount": Decimal("42.50"),
                        "currency_code": "CLP",
                        "publication_date": datetime(2026, 4, 1, tzinfo=UTC),
                        "close_date": datetime(2026, 4, 30, tzinfo=UTC),
                        "line_count": 2,
                        "bid_count": 1,
                        "supplier_count": 1,
                        "purchase_order_count": 0,
                        "buyer_name": "Municipalidad",
                        "buyer_region": "RM",
                        "buyer_commune": "Santiago",
                        "primary_category": "Servicios",
                        "procurement_type": "public",
                        "is_less_than_100_utm": False,
                        "days_remaining": 3,
                        "derived_stage": "closing_soon",
                    }
                ]
            ),
        ]
    )

    payload = _list_opportunities(session)
    item = payload["items"][0]
    assert item["estimatedAmount"] == 42.5
    assert item["publicationDate"] == "2026-04-01T00:00:00+00:00"
    assert item["officialStatus"] == "Publicada"
    assert item["mpEstadoCodigo"] == 5
    assert item["mpEstadoCanonical"] == "publicada"
    assert item["dataSourceKind"] == "api_publicada"
    assert item["availabilityContext"] == "current_publicada_discovery"
    assert item["codigoTipo"] == "L1"
    assert item["tipoConvocatoria"] == "1"
    assert item["informada"] == "No"
    assert item["visibilidadMonto"] == "Visible"
    assert item["fuenteFinanciamiento"] == "Municipal"
    assert item["complaintCount"] == 3
    assert item["procurementType"] == "public"
    assert item["buyerCommune"] == "Santiago"
    assert item["lineCount"] == 2
    assert item["bidCount"] == 1
    assert item["supplierCount"] == 1
    assert item["purchaseOrderCount"] == 0


def test_opportunities_summary_maps_metric_indexes_to_labels() -> None:
    session = _DummySession(
        [
            _ScalarResult(
                (
                    10,
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    10,
                    Decimal("100.00"),
                    Decimal("500.00"),
                )
            ),
        ]
    )

    payload = get_opportunities_summary(db=session)  # type: ignore[arg-type]
    metrics = {metric["key"]: metric["value"] for metric in payload["metrics"]}
    assert metrics["total_opportunities"] == 10
    assert metrics["open"] == 2
    assert metrics["closing_soon"] == 3
    assert metrics["closed"] == 4
    assert metrics["revoked_or_suspended"] == 6
    assert metrics["mp_publicada"] == 7
    assert metrics["source_publicadas"] == 8
    assert metrics["availability_publicadas"] == 9
    assert metrics["avg_estimated_amount"] == 100.0
    assert metrics["total_estimated_amount"] == 500.0


def test_opportunity_detail_returns_line_certainty_contract() -> None:
    session = _DummySession(
        [
            _MappingResult(
                [
                    {
                        "notice_id": "123-1-LP26",
                        "external_notice_code": "123-1-LP26",
                        "title": "Compra de servicios",
                        "notice_description_raw": "Detalle de servicios",
                        "official_status": "Publicada",
                        "mp_estado_codigo": 5,
                        "mp_estado_nombre": "Publicada",
                        "mp_estado_canonical": "publicada",
                        "data_source_kind": "api_publicada",
                        "availability_context": "current_publicada_discovery",
                        "codigo_tipo": "L1",
                        "tipo": "Licitacion Publica",
                        "tipo_convocatoria": "1",
                        "informada": "No",
                        "visibilidad_monto": "Visible",
                        "fuente_financiamiento": "Municipal",
                        "complaint_count": 4,
                        "estimated_amount": Decimal("42.50"),
                        "currency_code": "CLP",
                        "publication_date": datetime(2026, 4, 1, tzinfo=UTC),
                        "close_date": datetime(2026, 4, 30, tzinfo=UTC),
                        "award_date": None,
                        "estimated_award_date": None,
                        "created_date": None,
                        "buyer_name": "Municipalidad",
                        "buyer_region": "RM",
                        "buyer_commune": "Santiago",
                        "contracting_unit_code": "U-1",
                        "contracting_unit_name": "Compras",
                        "derived_stage": "closing_soon",
                    }
                ]
            ),
            _MappingResult(
                [
                    {
                        "item_code": "ITEM-1",
                        "correlative": 1,
                        "product_code_onu": "78111808",
                        "line_name": "Arriendo",
                        "line_description": "Arriendo de vehiculos",
                        "category": "Servicios",
                        "quantity": Decimal("2"),
                        "unit": "unidad",
                        "offer_count": 3,
                        "selected_offer_count": 1,
                        "supplier_count": 2,
                        "related_purchase_order_item_count": 1,
                        "relationship_certainty": "medium",
                    }
                ]
            ),
            _MappingResult(
                [
                    {
                        "supplier_code": "codigo:77",
                        "supplier_name": "Proveedor Uno",
                        "offer_name": "Oferta tecnica",
                        "item_code": "ITEM-1",
                        "offer_status": "Aceptada",
                        "offered_amount": Decimal("40.00"),
                        "unit_price": Decimal("20.00"),
                        "offered_quantity": Decimal("2"),
                        "currency_code": "CLP",
                        "is_selected": True,
                        "submitted_at": datetime(2026, 4, 2, tzinfo=UTC),
                    }
                ]
            ),
            _MappingResult(
                [
                    {
                        "purchase_order_code": "PO-1",
                        "purchase_order_status": "ACEPTADA",
                        "purchase_order_created_at": datetime(2026, 4, 5, tzinfo=UTC),
                        "purchase_order_amount": Decimal("100.00"),
                        "currency_code": "CLP",
                    }
                ]
            ),
        ]
    )

    payload = get_opportunity_detail("123-1-LP26", db=session)  # type: ignore[arg-type]

    assert payload["relationshipSummary"] == "medium"
    assert payload["mpEstadoCodigo"] == 5
    assert payload["dataSourceKind"] == "api_publicada"
    assert payload["availabilityContext"] == "current_publicada_discovery"
    assert payload["codigoTipo"] == "L1"
    assert payload["tipoConvocatoria"] == "1"
    assert payload["informada"] == "No"
    assert payload["visibilidadMonto"] == "Visible"
    assert payload["fuenteFinanciamiento"] == "Municipal"
    assert payload["complaintCount"] == 4
    assert payload["noticeDescriptionRaw"] == "Detalle de servicios"
    assert payload["buyer"]["buyerCommune"] == "Santiago"
    assert payload["participantsAvailability"] == "available"
    assert payload["offersAvailability"] == "available"
    assert payload["awardAvailability"] == "not_yet_public"
    assert payload["purchaseOrderAvailability"] == "available"
    assert payload["descriptionAvailability"] == "available"
    assert payload["lines"][0]["correlative"] == 1
    assert payload["lines"][0]["selectedOfferCount"] == 1
    assert payload["lines"][0]["relatedPurchaseOrderItemCount"] == 1
    assert payload["lines"][0]["relationshipCertainty"] == "medium"
    assert payload["timeline"][0]["date"] == "2026-04-01T00:00:00+00:00"
    assert payload["timeline"][1]["date"] == "2026-04-30T00:00:00+00:00"
    assert payload["offers"][0]["supplierName"] == "Proveedor Uno"
    assert payload["offers"][0]["offerName"] == "Oferta tecnica"
    assert payload["offers"][0]["unitPrice"] == 20.0
    assert payload["offers"][0]["offeredQuantity"] == 2.0
    assert payload["purchaseOrders"][0]["purchaseOrderCode"] == "PO-1"
    assert payload["purchaseOrders"][0]["purchaseOrderAmount"] == 100.0
    assert payload["purchaseOrders"][0]["relationshipCertainty"] == "unconfirmed"
    assert payload["purchaseOrders"][0]["purchaseOrderItemId"] is None


def test_opportunity_detail_publicada_missing_postclose_data_is_not_yet_public() -> None:
    session = _DummySession(
        [
            _MappingResult(
                [
                    {
                        "notice_id": "200-1-LP26",
                        "external_notice_code": "200-1-LP26",
                        "title": "Compra abierta",
                        "notice_description_raw": None,
                        "official_status": "Publicada",
                        "mp_estado_codigo": 5,
                        "mp_estado_nombre": "Publicada",
                        "mp_estado_canonical": "publicada",
                        "data_source_kind": "api_publicada",
                        "availability_context": "current_publicada_discovery",
                        "codigo_tipo": "L1",
                        "tipo": "Licitacion Publica",
                        "tipo_convocatoria": "1",
                        "informada": "No",
                        "visibilidad_monto": "Visible",
                        "fuente_financiamiento": None,
                        "complaint_count": 1,
                        "estimated_amount": None,
                        "currency_code": "CLP",
                        "publication_date": datetime(2026, 4, 1, tzinfo=UTC),
                        "close_date": datetime(2026, 4, 30, tzinfo=UTC),
                        "award_date": None,
                        "estimated_award_date": None,
                        "created_date": None,
                        "buyer_name": "Municipalidad",
                        "buyer_region": "RM",
                        "buyer_commune": "Santiago",
                        "contracting_unit_code": "U-1",
                        "contracting_unit_name": "Compras",
                        "derived_stage": "closing_soon",
                    }
                ]
            ),
            _MappingResult([]),
            _MappingResult([]),
            _MappingResult([]),
        ]
    )

    payload = get_opportunity_detail("200-1-LP26", db=session)  # type: ignore[arg-type]

    assert payload["participantsAvailability"] == "not_yet_public"
    assert payload["offersAvailability"] == "not_yet_public"
    assert payload["awardAvailability"] == "not_yet_public"
    assert payload["purchaseOrderAvailability"] == "not_yet_public"
    assert payload["descriptionAvailability"] == "pending_detail"
    assert payload["offersAvailability"] != "pipeline_missing"
    assert payload["purchaseOrderAvailability"] != "pipeline_missing"


def test_opportunity_detail_informada_without_offers_is_not_reported_by_source() -> None:
    session = _DummySession(
        [
            _MappingResult(
                [
                    {
                        "notice_id": "201-1-LP26",
                        "external_notice_code": "201-1-LP26",
                        "title": "Compra informada",
                        "notice_description_raw": "Proceso informado",
                        "official_status": "Publicada",
                        "mp_estado_codigo": 5,
                        "mp_estado_nombre": "Publicada",
                        "mp_estado_canonical": "publicada",
                        "data_source_kind": "api_detail",
                        "availability_context": "current_publicada_detail",
                        "codigo_tipo": "L1",
                        "tipo": "Licitacion Publica",
                        "tipo_convocatoria": "1",
                        "informada": "Si",
                        "visibilidad_monto": "Visible",
                        "fuente_financiamiento": None,
                        "complaint_count": None,
                        "estimated_amount": None,
                        "currency_code": "CLP",
                        "publication_date": datetime(2026, 4, 1, tzinfo=UTC),
                        "close_date": datetime(2026, 4, 30, tzinfo=UTC),
                        "award_date": None,
                        "estimated_award_date": None,
                        "created_date": None,
                        "buyer_name": "Municipalidad",
                        "buyer_region": "RM",
                        "buyer_commune": "Santiago",
                        "contracting_unit_code": "U-1",
                        "contracting_unit_name": "Compras",
                        "derived_stage": "closing_soon",
                    }
                ]
            ),
            _MappingResult([]),
            _MappingResult([]),
            _MappingResult([]),
        ]
    )

    payload = get_opportunity_detail("201-1-LP26", db=session)  # type: ignore[arg-type]

    assert payload["participantsAvailability"] == "not_reported_by_source"
    assert payload["offersAvailability"] == "not_reported_by_source"
    assert payload["awardAvailability"] == "not_yet_public"
    assert payload["purchaseOrderAvailability"] == "not_yet_public"


def test_opportunity_detail_non_publicada_missing_data_marks_pipeline_missing() -> None:
    session = _DummySession(
        [
            _MappingResult(
                [
                    {
                        "notice_id": "300-1-LP26",
                        "external_notice_code": "300-1-LP26",
                        "title": "Compra cerrada",
                        "notice_description_raw": None,
                        "official_status": "Adjudicada",
                        "mp_estado_codigo": 8,
                        "mp_estado_nombre": "Adjudicada",
                        "mp_estado_canonical": "adjudicada",
                        "data_source_kind": None,
                        "availability_context": "historical_full_cycle",
                        "codigo_tipo": "L1",
                        "tipo": "Licitacion Publica",
                        "tipo_convocatoria": "1",
                        "informada": "No",
                        "visibilidad_monto": "Visible",
                        "fuente_financiamiento": None,
                        "complaint_count": None,
                        "estimated_amount": None,
                        "currency_code": "CLP",
                        "publication_date": datetime(2026, 4, 1, tzinfo=UTC),
                        "close_date": datetime(2026, 4, 30, tzinfo=UTC),
                        "award_date": None,
                        "estimated_award_date": None,
                        "created_date": None,
                        "buyer_name": "Municipalidad",
                        "buyer_region": "RM",
                        "buyer_commune": "Santiago",
                        "contracting_unit_code": "U-1",
                        "contracting_unit_name": "Compras",
                        "derived_stage": "closed",
                    }
                ]
            ),
            _MappingResult([]),
            _MappingResult([]),
            _MappingResult([]),
        ]
    )

    payload = get_opportunity_detail("300-1-LP26", db=session)  # type: ignore[arg-type]

    assert payload["participantsAvailability"] == "pipeline_missing"
    assert payload["offersAvailability"] == "pipeline_missing"
    assert payload["awardAvailability"] == "pipeline_missing"
    assert payload["purchaseOrderAvailability"] == "pipeline_missing"
    assert payload["descriptionAvailability"] == "pipeline_missing"


def test_opportunity_detail_api_detail_missing_description_is_not_reported_by_source() -> None:
    session = _DummySession(
        [
            _MappingResult(
                [
                    {
                        "notice_id": "301-1-LP26",
                        "external_notice_code": "301-1-LP26",
                        "title": "Compra detalle sin descripcion",
                        "notice_description_raw": None,
                        "official_status": "Publicada",
                        "mp_estado_codigo": 5,
                        "mp_estado_nombre": "Publicada",
                        "mp_estado_canonical": "publicada",
                        "data_source_kind": "api_detail",
                        "availability_context": "current_publicada_detail",
                        "codigo_tipo": "L1",
                        "tipo": "Licitacion Publica",
                        "tipo_convocatoria": "1",
                        "informada": "No",
                        "visibilidad_monto": "Visible",
                        "fuente_financiamiento": None,
                        "complaint_count": 2,
                        "estimated_amount": None,
                        "currency_code": "CLP",
                        "publication_date": datetime(2026, 4, 1, tzinfo=UTC),
                        "close_date": datetime(2026, 4, 30, tzinfo=UTC),
                        "award_date": None,
                        "estimated_award_date": None,
                        "created_date": None,
                        "buyer_name": "Municipalidad",
                        "buyer_region": "RM",
                        "buyer_commune": "Santiago",
                        "contracting_unit_code": "U-1",
                        "contracting_unit_name": "Compras",
                        "derived_stage": "closing_soon",
                    }
                ]
            ),
            _MappingResult([]),
            _MappingResult([]),
            _MappingResult([]),
        ]
    )

    payload = get_opportunity_detail("301-1-LP26", db=session)  # type: ignore[arg-type]

    assert payload["descriptionAvailability"] == "not_reported_by_source"


def test_opportunities_accepts_extended_filters() -> None:
    session = _DummySession([_ScalarResult((0,)), _MappingResult([])])

    _list_opportunities(
        session,
        official_status="Publicada",
        buyer_region="RM",
        primary_category="Servicios",
        publication_from=date(2026, 1, 1),
        publication_to=date(2026, 12, 31),
        close_from=date(2026, 4, 1),
        close_to=date(2026, 4, 30),
        max_amount=Decimal("100"),
        procurement_type="public",
        less_than_100_utm=True,
        source_view="publicadas",
    )

    params = session.params[0]
    assert params["official_status"] == "%Publicada%"
    assert params["buyer_region"] == "%RM%"
    assert params["primary_category"] == "%Servicios%"
    assert params["max_amount"] == Decimal("100")
    assert params["procurement_type"] == "public"
    assert params["less_than_100_utm"] is True
    assert params["source_view"] == "publicadas"


def test_opportunities_queries_coalesce_display_fields_with_normalized_fallback() -> None:
    list_sql = LIST_SQL.text
    detail_sql = DETAIL_SQL.text
    summary_sql = SUMMARY_SQL.text

    assert "coalesce(sn.notice_title, bi.normalized_title) as title" in list_sql
    assert "coalesce(sn.notice_status_name, bi.normalized_official_status) as official_status" in list_sql
    assert "coalesce(sn.estimated_amount, bi.normalized_estimated_amount) as estimated_amount" in list_sql
    assert "coalesce(sn.publication_date, bi.normalized_publication_date) as publication_date" in list_sql
    assert "coalesce(sn.close_date, bi.normalized_close_date) as close_date" in list_sql
    assert "coalesce(sn.complaint_count, ls.snapshot_complaint_count) as complaint_count" in list_sql
    assert "coalesce(bi.buyer_commune, ls.snapshot_buyer_commune) as buyer_commune" in list_sql
    assert "nullif(trim(asp.payload_json ->> 'Informada'), '') as informada" in list_sql
    assert "when m.source_mode = 'detail-by-codigo' then 0" in list_sql
    assert "coalesce(sn.mp_estado_codigo, ls.snapshot_mp_estado_codigo) as mp_estado_codigo" in detail_sql
    assert "coalesce(sn.complaint_count, ls.snapshot_complaint_count) as complaint_count" in detail_sql
    assert "coalesce(sn.notice_status_name, bi.normalized_official_status)" in detail_sql
    assert "coalesce(sn.close_date, nl.fecha_cierre)" in summary_sql
