from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.shared.cleaning import is_licitacion_elegible, normalize_text_base, normalize_tipo_adquisicion

DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
)

NUMERIC_20_6_MAX_ABS = Decimal("99999999999999.999999")


def clean_raw_value(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if text == "":
        return None
    if text.upper() in {"NA", "N/A", "NULL"}:
        return None
    if text in {"1900-01-01", "0001-01-01", "01-01-1900", "01/01/1900"}:
        return None
    if text in {
        "1900-01-01 00:00:00",
        "0001-01-01 00:00:00",
        "01-01-1900 00:00:00",
        "01/01/1900 00:00:00",
    }:
        return None
    return text


def pick(raw: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        if key in raw:
            raw_value = raw.get(key)
            if raw_value is not None:
                if isinstance(raw_value, dict):
                    # Sanitize corrupted dict values to str to prevent SQLAlchemy 'can't adapt type' error
                    value = clean_raw_value(str(raw_value))
                else:
                    value = clean_raw_value(raw_value)
                if value is not None:
                    return value
    return None


def parse_decimal(value: Any) -> Decimal | None:
    raw = clean_raw_value(value)
    if raw is None:
        return None

    text = raw.replace("\xa0", "").replace(" ", "")
    text = re.sub(r"[^0-9,.\-+eE]", "", text)

    # Examples handled:
    # - 1.234,56  -> 1234.56
    # - 1234,56   -> 1234.56
    # - 6,8e+08   -> 6.8e+08
    # - 1,234.56  -> 1234.56
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None

    if not parsed.is_finite():
        return None
    if abs(parsed) > NUMERIC_20_6_MAX_ABS:
        return None
    return parsed


def parse_int(value: Any) -> int | None:
    number = parse_decimal(value)
    if number is None:
        return None
    try:
        return int(number)
    except (ValueError, ArithmeticError):
        return None


def parse_datetime(value: Any) -> datetime | None:
    raw = clean_raw_value(value)
    if raw is None:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def parse_bool(value: Any) -> bool | None:
    raw = clean_raw_value(value)
    if raw is None:
        return None

    norm = normalize_text_base(raw)
    if norm is None:
        return None

    if norm in {"1", "true", "si", "s", "yes", "y", "x", "seleccionada", "verdadero"}:
        return True
    if norm in {"0", "false", "no", "n", "no seleccionada", "falso"}:
        return False
    return None


def tipo_flags(tipo_adquisicion: str | None) -> dict[str, bool]:
    normalized = normalize_tipo_adquisicion(tipo_adquisicion) or ""
    flag_publica = "licitacion publica" in normalized
    flag_privada = "licitacion privada" in normalized
    flag_servicios = (
        "servicios personales especializados" in normalized
        or "licitacion de servicios" in normalized
    )
    flag_menos_100 = ("menor a 100 utm" in normalized) or ("inferior a 100 utm" in normalized)
    return {
        "flag_licitacion_publica": flag_publica,
        "flag_licitacion_privada": flag_privada,
        "flag_licitacion_servicios": flag_servicios,
        "flag_menos_100_utm": flag_menos_100,
        "is_elegible_mvp": is_licitacion_elegible(tipo_adquisicion),
    }


def oferta_key_from_raw(raw: dict[str, Any]) -> str:
    parts = [
        pick(raw, "CodigoExterno") or "",
        pick(raw, "Codigoitem", "CodigoItem") or "",
        pick(raw, "Correlativo") or "",
        pick(raw, "CodigoProveedor") or "",
        pick(raw, "RutProveedor") or "",
        pick(raw, "Nombre de la Oferta") or "",
        pick(raw, "FechaEnvioOferta") or "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def build_licitacion_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    codigo_externo = pick(raw, "CodigoExterno")
    codigo = pick(raw, "Codigo")
    if not codigo_externo or not codigo:
        return None

    tipo_raw = pick(raw, "Tipo de Adquisicion")
    flags = tipo_flags(tipo_raw)

    fecha_publicacion = parse_datetime(pick(raw, "FechaPublicacion"))
    fecha_cierre = parse_datetime(pick(raw, "FechaCierre"))
    cantidad_dias = None
    if fecha_publicacion is not None and fecha_cierre is not None:
        cantidad_dias = (fecha_cierre - fecha_publicacion).days

    return {
        "codigo_externo": codigo_externo,
        "codigo": codigo,
        "nombre": pick(raw, "Nombre"),
        "descripcion": pick(raw, "Descripcion"),
        "tipo_adquisicion": tipo_raw,
        "tipo_adquisicion_norm": normalize_tipo_adquisicion(tipo_raw),
        "codigo_estado": parse_int(pick(raw, "CodigoEstado")),
        "estado": pick(raw, "Estado"),
        "tipo": pick(raw, "Tipo"),
        "tipo_convocatoria": pick(raw, "TipoConvocatoria"),
        "moneda_adquisicion": pick(raw, "Moneda Adquisicion"),
        "visibilidad_monto_raw": pick(raw, "VisibilidadMonto"),
        "monto_estimado": parse_decimal(pick(raw, "MontoEstimado")),
        "numero_oferentes": parse_int(pick(raw, "NumeroOferentes")),
        "codigo_organismo": pick(raw, "CodigoOrganismo"),
        "nombre_organismo": pick(raw, "NombreOrganismo"),
        "codigo_unidad": pick(raw, "CodigoUnidad"),
        "nombre_unidad": pick(raw, "NombreUnidad"),
        "comuna_unidad": pick(raw, "ComunaUnidad"),
        "region_unidad": pick(raw, "RegionUnidad"),
        "fecha_publicacion": fecha_publicacion,
        "fecha_cierre": fecha_cierre,
        "fecha_adjudicacion": parse_datetime(pick(raw, "FechaAdjudicacion")),
        "fecha_estimada_adjudicacion": parse_datetime(pick(raw, "FechaEstimadaAdjudicacion")),
        "fecha_inicio": parse_datetime(pick(raw, "FechaInicio")),
        "fecha_final": parse_datetime(pick(raw, "FechaFinal")),
        "cantidad_dias_licitacion": cantidad_dias,
        "flag_licitacion_publica": flags["flag_licitacion_publica"],
        "flag_licitacion_privada": flags["flag_licitacion_privada"],
        "flag_licitacion_servicios": flags["flag_licitacion_servicios"],
        "flag_menos_100_utm": flags["flag_menos_100_utm"],
        "is_elegible_mvp": flags["is_elegible_mvp"],
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_licitacion_item_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    codigo_externo = pick(raw, "CodigoExterno")
    codigo_item = pick(raw, "Codigoitem", "CodigoItem")
    if not codigo_externo or not codigo_item:
        return None

    return {
        "codigo_externo": codigo_externo,
        "codigo_item": codigo_item,
        "correlativo": pick(raw, "Correlativo"),
        "codigo_producto_onu": pick(raw, "CodigoProductoONU"),
        "nombre_producto_generico": pick(raw, "Nombre producto genrico"),
        "nombre_linea_adquisicion": pick(raw, "Nombre linea Adquisicion"),
        "descripcion_linea_adquisicion": pick(raw, "Descripcion linea Adquisicion"),
        "unidad_medida": pick(raw, "UnidadMedida"),
        "cantidad": parse_decimal(pick(raw, "Cantidad")),
        "rubro1": pick(raw, "Rubro1"),
        "rubro2": pick(raw, "Rubro2"),
        "rubro3": pick(raw, "Rubro3"),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_oferta_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    codigo_externo = pick(raw, "CodigoExterno")
    if not codigo_externo:
        return None

    offer_signal = any(
        pick(raw, col) is not None for col in ("NombreProveedor", "Nombre de la Oferta", "Estado Oferta")
    )
    if not offer_signal:
        return None

    supplier_identity = any(pick(raw, col) is not None for col in ("CodigoProveedor", "RutProveedor"))
    if not supplier_identity:
        return None

    return {
        "oferta_key_sha256": oferta_key_from_raw(raw),
        "codigo_externo": codigo_externo,
        "codigo_item": pick(raw, "Codigoitem", "CodigoItem"),
        "correlativo": pick(raw, "Correlativo"),
        "codigo_proveedor": pick(raw, "CodigoProveedor"),
        "rut_proveedor": pick(raw, "RutProveedor"),
        "nombre_proveedor": pick(raw, "NombreProveedor"),
        "razon_social_proveedor": pick(raw, "RazonSocialProveedor"),
        "estado_oferta": pick(raw, "Estado Oferta"),
        "nombre_oferta": pick(raw, "Nombre de la Oferta"),
        "cantidad_ofertada": parse_decimal(pick(raw, "Cantidad Ofertada")),
        "monto_unitario_oferta": parse_decimal(pick(raw, "MontoUnitarioOferta")),
        "valor_total_ofertado": parse_decimal(pick(raw, "Valor Total Ofertado")),
        "oferta_seleccionada": parse_bool(pick(raw, "Oferta seleccionada")),
        "fecha_envio_oferta": parse_datetime(pick(raw, "FechaEnvioOferta")),
        "cantidad_adjudicada": parse_decimal(pick(raw, "CantidadAdjudicada")),
        "monto_linea_adjudica": parse_decimal(pick(raw, "MontoLineaAdjudica")),
        "monto_estimado_adjudicado": parse_decimal(pick(raw, "Monto Estimado Adjudicado")),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_orden_compra_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    codigo_oc = pick(raw, "Codigo")
    if not codigo_oc:
        return None

    codigo_licitacion = pick(raw, "CodigoLicitacion")
    return {
        "codigo_oc": codigo_oc,
        "id_oc_raw": pick(raw, "ID"),
        "link": pick(raw, "Link"),
        "nombre": pick(raw, "Nombre"),
        "descripcion_observaciones": pick(raw, "Descripcion/Obervaciones"),
        "tipo": pick(raw, "Tipo"),
        "procedencia_oc": pick(raw, "ProcedenciaOC"),
        "es_trato_directo": parse_bool(pick(raw, "EsTratoDirecto")),
        "es_compra_agil": parse_bool(pick(raw, "EsCompraAgil")),
        "codigo_tipo": pick(raw, "CodigoTipo"),
        "codigo_abreviado_tipo_oc": pick(raw, "CodigoAbreviadoTipoOC"),
        "descripcion_tipo_oc": pick(raw, "DescripcionTipoOC"),
        "codigo_estado": pick(raw, "codigoEstado"),
        "estado": pick(raw, "Estado"),
        "codigo_estado_proveedor": pick(raw, "codigoEstadoProveedor"),
        "estado_proveedor": pick(raw, "EstadoProveedor"),
        "fecha_creacion": parse_datetime(pick(raw, "FechaCreacion")),
        "fecha_envio": parse_datetime(pick(raw, "FechaEnvio")),
        "fecha_solicitud_cancelacion": parse_datetime(pick(raw, "FechaSolicitudCancelacion")),
        "fecha_aceptacion": parse_datetime(pick(raw, "FechaAceptacion")),
        "fecha_cancelacion": parse_datetime(pick(raw, "FechaCancelacion")),
        "fecha_ultima_modificacion": parse_datetime(pick(raw, "fechaUltimaModificacion")),
        "tiene_items": parse_bool(pick(raw, "tieneItems")),
        "promedio_calificacion": parse_decimal(pick(raw, "PromedioCalificacion")),
        "cantidad_evaluacion": parse_int(pick(raw, "CantidadEvaluacion")),
        "tipo_moneda_oc": pick(raw, "TipoMonedaOC"),
        "monto_total_oc": parse_decimal(pick(raw, "MontoTotalOC")),
        "monto_total_oc_pesos_chilenos": parse_decimal(pick(raw, "MontoTotalOC_PesosChilenos")),
        "impuestos": parse_decimal(pick(raw, "Impuestos")),
        "tipo_impuesto": pick(raw, "TipoImpuesto"),
        "descuentos": parse_decimal(pick(raw, "Descuentos")),
        "cargos": parse_decimal(pick(raw, "Cargos")),
        "total_neto_oc": parse_decimal(pick(raw, "TotalNetoOC")),
        "total_cargos": parse_decimal(pick(raw, "totalCargos")),
        "total_descuentos": parse_decimal(pick(raw, "totalDescuentos")),
        "total_impuestos": parse_decimal(pick(raw, "totalImpuestos")),
        "porcentaje_iva": parse_decimal(pick(raw, "PorcentajeIva")),
        "codigo_licitacion": codigo_licitacion,
        "codigo_convenio_marco": pick(raw, "Codigo_ConvenioMarco"),
        "has_codigo_licitacion": codigo_licitacion is not None,
        "codigo_unidad_compra": pick(raw, "CodigoUnidadCompra"),
        "rut_unidad_compra": pick(raw, "RutUnidadCompra"),
        "unidad_compra": pick(raw, "UnidadCompra"),
        "codigo_organismo_publico": pick(raw, "CodigoOrganismoPublico"),
        "organismo_publico": pick(raw, "OrganismoPublico"),
        "sector": pick(raw, "sector"),
        "actividad_comprador": pick(raw, "ActividadComprador"),
        "ciudad_unidad_compra": pick(raw, "CiudadUnidadCompra"),
        "region_unidad_compra": pick(raw, "RegionUnidadCompra"),
        "pais_unidad_compra": pick(raw, "PaisUnidadCompra"),
        "codigo_sucursal": pick(raw, "CodigoSucursal"),
        "rut_sucursal": pick(raw, "RutSucursal"),
        "sucursal": pick(raw, "Sucursal"),
        "codigo_proveedor": pick(raw, "CodigoProveedor"),
        "nombre_proveedor": pick(raw, "NombreProveedor"),
        "actividad_proveedor": pick(raw, "ActividadProveedor"),
        "comuna_proveedor": pick(raw, "ComunaProveedor"),
        "region_proveedor": pick(raw, "RegionProveedor"),
        "pais_proveedor": pick(raw, "PaisProveedor"),
        "financiamiento": pick(raw, "Financiamiento"),
        "pais": pick(raw, "Pais"),
        "tipo_despacho": pick(raw, "TipoDespacho"),
        "forma_pago": pick(raw, "Forma de Pago", "FormaPago"),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_orden_compra_item_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
) -> dict[str, Any] | None:
    codigo_oc = pick(raw, "Codigo")
    id_item = pick(raw, "IDItem")
    if not codigo_oc or not id_item:
        return None

    return {
        "codigo_oc": codigo_oc,
        "id_item": id_item,
        "codigo_producto_onu": pick(raw, "codigoProductoONU"),
        "codigo_categoria": pick(raw, "codigoCategoria"),
        "categoria": pick(raw, "Categoria"),
        "nombre_producto_generico": pick(raw, "NombreroductoGenerico", "NombreProductoGenerico"),
        "rubro_n1": pick(raw, "RubroN1"),
        "rubro_n2": pick(raw, "RubroN2"),
        "rubro_n3": pick(raw, "RubroN3"),
        "especificacion_comprador": pick(raw, "EspecificacionComprador"),
        "especificacion_proveedor": pick(raw, "EspecificacionProveedor"),
        "cantidad": parse_decimal(pick(raw, "cantidad")),
        "unidad_medida": pick(raw, "UnidadMedida"),
        "moneda_item": pick(raw, "monedaItem"),
        "precio_neto": parse_decimal(pick(raw, "precioNeto")),
        "total_cargos": parse_decimal(pick(raw, "totalCargos")),
        "total_descuentos": parse_decimal(pick(raw, "totalDescuentos")),
        "total_impuestos": parse_decimal(pick(raw, "totalImpuestos")),
        "total_linea_neto": parse_decimal(pick(raw, "totalLineaNeto")),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }
