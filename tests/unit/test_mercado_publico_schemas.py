from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from backend.integrations.mercado_publico.schemas import parse_licitaciones_response


def test_parse_active_discovery_payload() -> None:
    payload = {
        "Codigo": 0,
        "Descripcion": "OK",
        "FechaCreacion": "2026-05-08",
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoExterno": "1274285-76-LR25",
                "Nombre": "Servicio de soporte",
                "CodigoEstado": 5,
                "Estado": "Publicada",
                "FechaPublicacion": "08052026",
                "FechaCierre": "12052026",
                "CodigoOrganismo": "1234",
                "NombreOrganismo": "Municipalidad X",
                "CodigoUnidad": "U-10",
                "NombreUnidad": "Compras",
                "Moneda": "CLP",
                "MontoEstimado": "1500000",
            }
        ],
    }

    response = parse_licitaciones_response(payload)
    assert response.code == 0
    assert response.count == 1
    assert response.notices[0].external_notice_code == "1274285-76-LR25"
    assert response.notices[0].publication_date is not None
    assert response.notices[0].close_date is not None
    assert response.notices[0].estimated_amount == Decimal("1500000")


def test_parse_rolling_window_payload() -> None:
    payload = {
        "Codigo": 0,
        "Descripcion": "OK",
        "FechaCreacion": "08/05/2026",
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoExterno": "2000000-10-LQ26",
                "Nombre": "Adquisicion de equipos",
                "CodigoEstado": 5,
                "Estado": "Publicada",
                "FechaPublicacion": "07/05/2026",
                "FechaCierre": "14/05/2026",
            }
        ],
    }

    response = parse_licitaciones_response(payload)
    assert response.created_at is not None
    assert response.notices[0].external_notice_code == "2000000-10-LQ26"
    assert response.notices[0].publication_date is not None
    assert response.notices[0].close_date is not None


def test_parse_detail_by_codigo_payload_with_nulls() -> None:
    payload = {
        "Codigo": 0,
        "Descripcion": "OK",
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoExterno": "3000000-20-LR26",
                "Nombre": "Licitacion detallada",
                "CodigoEstado": 5,
                "Estado": "Publicada",
                "FechaPublicacion": "2026-05-08",
                "FechaCierre": None,
                "CodigoOrganismo": None,
                "NombreOrganismo": "",
                "Moneda": None,
            }
        ],
    }

    response = parse_licitaciones_response(payload)
    notice = response.notices[0]
    assert notice.external_notice_code == "3000000-20-LR26"
    assert notice.close_date is None
    assert notice.buyer_org_code is None
    assert notice.currency_code is None
    assert notice.estimated_amount is None


def test_parse_active_discovery_payload_with_datetime_strings_and_missing_top_level_fields() -> None:
    payload = {
        "Cantidad": 1,
        "FechaCreacion": "2026-05-08T06:01:53.969145Z",
        "Listado": [
            {
                "CodigoExterno": "1274285-76-LR25",
                "Nombre": "Servicio de soporte",
                "CodigoEstado": 5,
                "Estado": "Publicada",
                "FechaPublicacion": "2026-05-08T15:10:00",
                "FechaCierre": "2026-05-18T15:10:00",
            }
        ],
    }

    response = parse_licitaciones_response(payload)
    assert response.code is None
    assert response.description is None
    assert response.created_at is not None
    assert response.notices[0].publication_date is not None
    assert response.notices[0].close_date is not None


def test_parse_detail_payload_discards_description() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "detail_by_codigo_payload.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    response = parse_licitaciones_response(payload)
    notice = response.notices[0]

    assert notice.description is not None, (
        "FAIL (expected): Descripcion is silently discarded by extra='ignore' "
        "-- LicitacionNotice has no description field"
    )


def test_parse_detail_payload_discards_nested_buyer() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "detail_by_codigo_payload.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    response = parse_licitaciones_response(payload)
    notice = response.notices[0]

    assert notice.comprador is not None, (
        "FAIL (expected): Comprador nested object is silently discarded by extra='ignore' "
        "-- LicitacionNotice has no comprador field"
    )
    assert notice.comprador.region_unidad == "Metropolitana"
    assert notice.comprador.comuna_unidad == "Providencia"


def test_parse_detail_payload_discards_items() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "detail_by_codigo_payload.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    response = parse_licitaciones_response(payload)
    notice = response.notices[0]

    assert notice.items is not None, (
        "FAIL (expected): Items.Listado is silently discarded by extra='ignore' "
        "-- LicitacionNotice has no items field"
    )
    assert len(notice.items.listado) == 2
