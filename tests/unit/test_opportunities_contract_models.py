from __future__ import annotations

from backend.api.opportunities_contract import (
    OpportunityDetailResponse,
    OpportunityListResponse,
    OpportunitySummaryResponse,
)


def test_opportunity_list_response_contract_parses_expected_shape() -> None:
    payload = OpportunityListResponse.model_validate(
        {
            "items": [
                {
                    "noticeId": "123-1-LP26",
                    "externalNoticeCode": "123-1-LP26",
                    "title": "Compra",
                    "officialStatus": "Publicada",
                    "derivedStage": "closing_soon",
                    "estimatedAmount": 10.0,
                    "currencyCode": "CLP",
                    "publicationDate": "2026-04-01T00:00:00+00:00",
                    "closeDate": "2026-04-30T00:00:00+00:00",
                    "lineCount": 1,
                    "bidCount": 1,
                    "supplierCount": 1,
                    "purchaseOrderCount": 0,
                    "buyerName": "Municipalidad",
                    "buyerRegion": "RM",
                    "primaryCategory": "Servicios",
                    "procurementType": "public",
                    "isLessThan100Utm": False,
                    "daysRemaining": 2,
                }
            ],
            "total": 1,
            "page": 1,
            "pageSize": 20,
        }
    )
    assert payload.total == 1
    assert payload.items[0].derivedStage == "closing_soon"


def test_opportunity_summary_response_contract_parses_expected_shape() -> None:
    payload = OpportunitySummaryResponse.model_validate(
        {
            "metrics": [
                {"key": "total_opportunities", "label": "Total oportunidades", "value": 10},
            ]
        }
    )
    assert payload.metrics[0].key == "total_opportunities"


def test_opportunity_detail_response_contract_parses_expected_shape() -> None:
    payload = OpportunityDetailResponse.model_validate(
        {
            "noticeId": "123-1-LP26",
            "externalNoticeCode": "123-1-LP26",
            "title": "Compra",
            "officialStatus": "Publicada",
            "derivedStage": "closing_soon",
            "estimatedAmount": 42.5,
            "currencyCode": "CLP",
            "buyer": {
                "buyerName": "Municipalidad",
                "buyerRegion": "RM",
                "contractingUnitName": "Compras",
                "contractingUnitCode": "U-1",
            },
            "relationshipSummary": "medium",
            "timeline": [
                {
                    "key": "publication",
                    "label": "Publicación",
                    "date": "2026-04-01T00:00:00+00:00",
                    "source": "official",
                }
            ],
            "lines": [
                {
                    "itemCode": "ITEM-1",
                    "correlative": 1,
                    "productCodeOnu": "78111808",
                    "lineName": "Arriendo",
                    "lineDescription": "Arriendo de vehiculos",
                    "category": "Servicios",
                    "quantity": 2.0,
                    "unit": "unidad",
                    "offerCount": 3,
                    "selectedOfferCount": 1,
                    "supplierCount": 2,
                    "relatedPurchaseOrderItemCount": 1,
                    "relationshipCertainty": "medium",
                }
            ],
            "offers": [],
            "purchaseOrders": [
                {
                    "purchaseOrderCode": "PO-1",
                    "purchaseOrderStatus": "ACEPTADA",
                    "purchaseOrderCreatedAt": "2026-04-05T00:00:00+00:00",
                    "purchaseOrderAmount": 100.0,
                    "currencyCode": "CLP",
                    "purchaseOrderItemId": None,
                    "purchaseOrderItemProductCodeOnu": None,
                    "purchaseOrderItemNetTotal": None,
                    "relationshipCertainty": "unconfirmed",
                }
            ],
        }
    )
    assert payload.purchaseOrders[0].relationshipCertainty == "unconfirmed"
