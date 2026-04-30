from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from backend.api.routers.opportunities import (
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
                        "official_status": "Publicada",
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
    assert item["procurementType"] == "public"
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
                        "official_status": "Publicada",
                        "estimated_amount": Decimal("42.50"),
                        "currency_code": "CLP",
                        "publication_date": datetime(2026, 4, 1, tzinfo=UTC),
                        "close_date": datetime(2026, 4, 30, tzinfo=UTC),
                        "award_date": None,
                        "estimated_award_date": None,
                        "created_date": None,
                        "buyer_name": "Municipalidad",
                        "buyer_region": "RM",
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
            _MappingResult([]),
        ]
    )

    payload = get_opportunity_detail("123-1-LP26", db=session)  # type: ignore[arg-type]

    assert payload["relationshipSummary"] == "medium"
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
    )

    params = session.params[0]
    assert params["official_status"] == "%Publicada%"
    assert params["buyer_region"] == "%RM%"
    assert params["primary_category"] == "%Servicios%"
    assert params["max_amount"] == Decimal("100")
    assert params["procurement_type"] == "public"
    assert params["less_than_100_utm"] is True
