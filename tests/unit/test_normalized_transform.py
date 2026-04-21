from datetime import datetime
from uuid import uuid4

from backend.normalized.transform import (
    build_licitacion_item_payload,
    build_licitacion_payload,
    build_orden_compra_item_payload,
    build_orden_compra_payload,
    build_oferta_payload,
    parse_bool,
    parse_datetime,
    parse_decimal,
)


def test_parse_decimal_handles_scientific_with_comma() -> None:
    value = parse_decimal("6,8e+08")
    assert value is not None
    assert str(value) == "6.8E+8"


def test_parse_datetime_handles_standard_format() -> None:
    value = parse_datetime("2026-01-15 13:45:00")
    assert value == datetime(2026, 1, 15, 13, 45, 0)


def test_parse_datetime_treats_sentinel_with_time_as_null() -> None:
    assert parse_datetime("1900-01-01 00:00:00") is None


def test_parse_bool_handles_selected_variants() -> None:
    assert parse_bool("Sí") is True
    assert parse_bool("No") is False
    assert parse_bool("1") is True
    assert parse_bool("0") is False


def test_build_licitacion_payload_derives_flags_and_days() -> None:
    raw = {
        "CodigoExterno": "L123",
        "Codigo": "123",
        "Nombre": "Licitacion test",
        "Tipo de Adquisicion": "Licitación Pública Menor a 100 UTM (L1)",
        "FechaPublicacion": "2026-01-01",
        "FechaCierre": "2026-01-11",
    }
    payload = build_licitacion_payload(raw, source_file_id=uuid4(), row_hash_sha256="abc")
    assert payload is not None
    assert payload["codigo_externo"] == "L123"
    assert payload["flag_licitacion_publica"] is True
    assert payload["flag_licitacion_privada"] is False
    assert payload["flag_menos_100_utm"] is True
    assert payload["is_elegible_mvp"] is True
    assert payload["cantidad_dias_licitacion"] == 10


def test_build_licitacion_item_payload_requires_keys() -> None:
    raw = {"CodigoExterno": "L123", "Codigoitem": "IT1", "Cantidad": "10,5"}
    payload = build_licitacion_item_payload(raw, source_file_id=uuid4(), row_hash_sha256="abc")
    assert payload is not None
    assert payload["codigo_item"] == "IT1"
    assert str(payload["cantidad"]) == "10.5"


def test_build_oferta_payload_skips_without_provider_signal() -> None:
    raw = {"CodigoExterno": "L123", "Codigoitem": "IT1"}
    payload = build_oferta_payload(raw, source_file_id=uuid4(), row_hash_sha256="abc")
    assert payload is None


def test_build_oferta_payload_requires_supplier_identity_keys() -> None:
    raw = {
        "CodigoExterno": "L123",
        "Codigoitem": "IT1",
        "Nombre de la Oferta": "oferta sin rut/codigo proveedor",
    }
    payload = build_oferta_payload(raw, source_file_id=uuid4(), row_hash_sha256="abc")
    assert payload is None


def test_parse_decimal_handles_currency_symbol_and_thousands() -> None:
    value = parse_decimal("$1.234,56")
    assert value is not None
    assert str(value) == "1234.56"


def test_parse_decimal_rejects_numeric_20_6_integer_overflow() -> None:
    assert parse_decimal("100000000000000") is None


def test_parse_decimal_accepts_numeric_20_6_upper_boundary() -> None:
    value = parse_decimal("99999999999999.999999")
    assert value is not None
    assert str(value) == "99999999999999.999999"


def test_parse_decimal_rejects_numeric_20_6_scale_overflow() -> None:
    assert parse_decimal("99999999999999.9999999") is None


def test_parse_decimal_rejects_large_scientific_overflow() -> None:
    assert parse_decimal("1e20") is None


def test_parse_bool_handles_full_spanish_booleans() -> None:
    assert parse_bool("verdadero") is True
    assert parse_bool("falso") is False


def test_build_orden_compra_payload_maps_core_fields() -> None:
    raw = {
        "ID": "999",
        "Codigo": "OC-1",
        "Estado": "Aceptada",
        "FechaEnvio": "2026-01-15 10:00:00",
        "CodigoLicitacion": "",
        "FormaPago": "Transferencia",
        "Forma de Pago": "Transferencia bancaria",
        "CodigoProveedor": "P-001",
        "CodigoUnidadCompra": "UC-01",
        "MontoTotalOC": "12345,67",
    }
    payload = build_orden_compra_payload(raw, source_file_id=uuid4(), row_hash_sha256="abc")
    assert payload is not None
    assert payload["id_oc_raw"] == "999"
    assert payload["codigo_oc"] == "OC-1"
    assert payload["estado"] == "Aceptada"
    assert payload["has_codigo_licitacion"] is False
    assert payload["forma_pago"] == "Transferencia bancaria"
    assert payload["codigo_proveedor"] == "P-001"
    assert payload["codigo_unidad_compra"] == "UC-01"
    assert str(payload["monto_total_oc"]) == "12345.67"


def test_build_orden_compra_item_payload_maps_line() -> None:
    raw = {
        "Codigo": "OC-1",
        "IDItem": "1",
        "codigoCategoria": "CAT-1",
        "Categoria": "insumos",
        "NombreroductoGenerico": "guantes",
        "RubroN1": "salud",
        "cantidad": "2",
        "UnidadMedida": "unidad",
        "monedaItem": "CLP",
        "precioNeto": "600",
        "totalCargos": "0",
        "totalDescuentos": "0",
        "totalImpuestos": "114",
        "totalLineaNeto": "1200",
    }
    payload = build_orden_compra_item_payload(raw, source_file_id=uuid4(), row_hash_sha256="abc")
    assert payload is not None
    assert payload["codigo_oc"] == "OC-1"
    assert payload["id_item"] == "1"
    assert payload["codigo_categoria"] == "CAT-1"
    assert payload["categoria"] == "insumos"
    assert payload["nombre_producto_generico"] == "guantes"
    assert payload["rubro_n1"] == "salud"
    assert payload["unidad_medida"] == "unidad"
    assert payload["moneda_item"] == "CLP"
    assert str(payload["cantidad"]) == "2"
    assert str(payload["precio_neto"]) == "600"
    assert str(payload["total_impuestos"]) == "114"
    assert str(payload["total_linea_neto"]) == "1200"
