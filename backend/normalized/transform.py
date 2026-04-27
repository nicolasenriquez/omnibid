from __future__ import annotations

from collections import Counter
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
DEFAULT_SILVER_NLP_VERSION = "silver_nlp_v1"
MAX_ANNOTATION_TOKENS = 128
MAX_ANNOTATION_NGRAMS = 24
ANNOTATION_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "health": ("salud", "hospital", "medic", "farmac", "clinica"),
    "construction": ("obra", "construccion", "infraestructura", "edificio", "mantencion vial"),
    "it_services": ("software", "licencia", "tecnolog", "comput", "servidor", "red"),
    "maintenance": ("mantencion", "mantenimiento", "reparacion", "soporte", "servicio tecnico"),
    "outsourcing": ("outsourcing", "externalizacion", "servicio externo"),
}


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


def parse_bool_or_false(value: Any) -> bool:
    return parse_bool(value) is True


BID_SUBMISSION_SIGNAL_COLUMNS: tuple[str, ...] = (
    "Nombre de la Oferta",
    "Estado Oferta",
    "FechaEnvioOferta",
)


def has_bid_submission_signal(raw: dict[str, Any]) -> bool:
    return any(pick(raw, col) is not None for col in BID_SUBMISSION_SIGNAL_COLUMNS)


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


def resolve_buyer_identity_key(raw: dict[str, Any]) -> str | None:
    return pick(raw, "CodigoUnidadCompra")


def resolve_supplier_identity_key(raw: dict[str, Any]) -> str | None:
    codigo_proveedor = pick(raw, "CodigoProveedor")
    if codigo_proveedor is not None:
        return f"codigo:{codigo_proveedor}"

    rut_proveedor = pick(raw, "RutProveedor")
    if rut_proveedor is not None:
        return f"rut:{rut_proveedor}"
    return None


def resolve_category_identity_key(raw: dict[str, Any]) -> str | None:
    category_code = pick(raw, "codigoCategoria")
    if category_code is not None:
        return category_code

    onu_code = pick(raw, "codigoProductoONU", "CodigoProductoONU")
    if onu_code is not None:
        # Prefix ONU fallback keys to avoid collisions with native category codes.
        return f"onu:{onu_code}"
    return None


def build_buyer_domain_payload(
    raw: dict[str, Any],
    source_file_id: Any,
) -> dict[str, Any] | None:
    buyer_key = resolve_buyer_identity_key(raw)
    if buyer_key is None:
        return None
    return {
        "buyer_key": buyer_key,
        "codigo_unidad_compra": buyer_key,
        "rut_unidad_compra": pick(raw, "RutUnidadCompra"),
        "unidad_compra": pick(raw, "UnidadCompra"),
        "codigo_organismo_publico": pick(raw, "CodigoOrganismoPublico"),
        "organismo_publico": pick(raw, "OrganismoPublico"),
        "sector": pick(raw, "sector"),
        "actividad_comprador": pick(raw, "ActividadComprador"),
        "ciudad_unidad_compra": pick(raw, "CiudadUnidadCompra"),
        "region_unidad_compra": pick(raw, "RegionUnidadCompra"),
        "pais_unidad_compra": pick(raw, "PaisUnidadCompra"),
        "source_file_id": source_file_id,
    }


def build_supplier_domain_payload(
    raw: dict[str, Any],
    source_file_id: Any,
) -> dict[str, Any] | None:
    supplier_key = resolve_supplier_identity_key(raw)
    if supplier_key is None:
        return None
    return {
        "supplier_key": supplier_key,
        "codigo_proveedor": pick(raw, "CodigoProveedor"),
        "rut_proveedor": pick(raw, "RutProveedor"),
        "nombre_proveedor": pick(raw, "NombreProveedor"),
        "razon_social_proveedor": pick(raw, "RazonSocialProveedor"),
        "actividad_proveedor": pick(raw, "ActividadProveedor"),
        "comuna_proveedor": pick(raw, "ComunaProveedor"),
        "region_proveedor": pick(raw, "RegionProveedor"),
        "pais_proveedor": pick(raw, "PaisProveedor"),
        "source_file_id": source_file_id,
    }


def build_category_domain_payload(
    raw: dict[str, Any],
    source_file_id: Any,
) -> dict[str, Any] | None:
    category_key = resolve_category_identity_key(raw)
    if category_key is None:
        return None
    return {
        "category_key": category_key,
        "codigo_categoria": category_key,
        "categoria": pick(raw, "Categoria"),
        "rubro_n1": pick(raw, "RubroN1"),
        "rubro_n2": pick(raw, "RubroN2"),
        "rubro_n3": pick(raw, "RubroN3"),
        "source_file_id": source_file_id,
    }


def resolve_buying_org_identity_key(raw: dict[str, Any]) -> str | None:
    return pick(raw, "CodigoOrganismoPublico", "CodigoOrganismo")


def resolve_contracting_unit_identity_key(raw: dict[str, Any]) -> str | None:
    return pick(raw, "CodigoUnidadCompra", "CodigoUnidad")


def resolve_category_ref_identity_key(raw: dict[str, Any]) -> str | None:
    category_code = pick(raw, "codigoCategoria")
    if category_code is not None:
        return f"cat:{category_code}"

    onu_code = pick(raw, "codigoProductoONU", "CodigoProductoONU")
    if onu_code is not None:
        return f"onu:{onu_code}"
    return None


def award_outcome_key_from_raw(raw: dict[str, Any]) -> str:
    parts = [
        pick(raw, "CodigoExterno") or "",
        pick(raw, "Codigoitem", "CodigoItem") or "",
        pick(raw, "CodigoProveedor") or "",
        pick(raw, "RutProveedor") or "",
        pick(raw, "CantidadAdjudicada") or "",
        pick(raw, "MontoLineaAdjudica") or "",
        pick(raw, "FechaAdjudicacion") or "",
        pick(raw, "Oferta seleccionada") or "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


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


def tokenize_annotation_text(text: str | None) -> list[str]:
    if text is None:
        return []
    normalized = normalize_text_base(text)
    if normalized is None:
        return []
    tokens = re.findall(r"[a-z0-9]+", normalized)
    if not tokens:
        return []
    return tokens[:MAX_ANNOTATION_TOKENS]


def top_ngrams_payload(tokens: list[str], *, max_ngrams: int = MAX_ANNOTATION_NGRAMS) -> list[dict[str, Any]]:
    if not tokens:
        return []

    counts = Counter(tokens)
    bigrams = [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]
    counts.update(bigrams)

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"ngram": ngram, "count": count} for ngram, count in ranked[:max_ngrams]]


def annotation_keyword_flags(tokens: list[str]) -> dict[str, bool]:
    text_blob = " ".join(tokens)
    flags: dict[str, bool] = {}
    for domain, keywords in ANNOTATION_DOMAIN_KEYWORDS.items():
        flags[domain] = any(keyword in text_blob for keyword in keywords)
    return flags


def semantic_tags_from_flags(flags: dict[str, bool]) -> list[str]:
    return [domain for domain, is_enabled in flags.items() if is_enabled]


def detect_annotation_language(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    return "es"


def tfidf_artifact_ref(
    *,
    scope: str,
    entity_id: str,
    text_clean: str | None,
    nlp_version: str,
) -> str | None:
    if text_clean is None:
        return None
    payload = f"{scope}|{entity_id}|{nlp_version}|{text_clean}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"tfidf://{scope}/{nlp_version}/{digest}"


def build_silver_notice_text_ann_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
    *,
    nlp_version: str = DEFAULT_SILVER_NLP_VERSION,
) -> dict[str, Any] | None:
    notice_id = pick(raw, "CodigoExterno")
    if notice_id is None:
        return None

    description_clean = normalize_text_base(pick(raw, "Descripcion"))
    tokens = tokenize_annotation_text(description_clean)
    keyword_flags = annotation_keyword_flags(tokens)
    domain_tags = semantic_tags_from_flags(keyword_flags)
    return {
        "notice_id": notice_id,
        "nlp_version": nlp_version,
        "corpus_scope": "notice_description",
        "language_detected": detect_annotation_language(tokens),
        "normalized_tokens_json": tokens,
        "top_ngrams_json": top_ngrams_payload(tokens),
        "keyword_flags_json": keyword_flags,
        "domain_tags_json": domain_tags,
        "semantic_category_label": domain_tags[0] if domain_tags else None,
        "tfidf_artifact_ref": tfidf_artifact_ref(
            scope="silver_notice",
            entity_id=notice_id,
            text_clean=description_clean,
            nlp_version=nlp_version,
        ),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_notice_line_text_ann_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
    *,
    nlp_version: str = DEFAULT_SILVER_NLP_VERSION,
) -> dict[str, Any] | None:
    notice_id = pick(raw, "CodigoExterno")
    item_code = pick(raw, "Codigoitem", "CodigoItem")
    if notice_id is None or item_code is None:
        return None

    line_description_clean = normalize_text_base(pick(raw, "Descripcion linea Adquisicion"))
    tokens = tokenize_annotation_text(line_description_clean)
    keyword_flags = annotation_keyword_flags(tokens)
    domain_tags = semantic_tags_from_flags(keyword_flags)
    return {
        "notice_id": notice_id,
        "item_code": item_code,
        "nlp_version": nlp_version,
        "corpus_scope": "notice_line_description",
        "language_detected": detect_annotation_language(tokens),
        "normalized_tokens_json": tokens,
        "top_ngrams_json": top_ngrams_payload(tokens),
        "keyword_flags_json": keyword_flags,
        "domain_tags_json": domain_tags,
        "semantic_category_label": domain_tags[0] if domain_tags else None,
        "tfidf_artifact_ref": tfidf_artifact_ref(
            scope="silver_notice_line",
            entity_id=f"{notice_id}:{item_code}",
            text_clean=line_description_clean,
            nlp_version=nlp_version,
        ),
        "source_file_id": source_file_id,
        "row_hash_sha256": row_hash_sha256,
    }


def build_silver_purchase_order_line_text_ann_payload(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
    *,
    nlp_version: str = DEFAULT_SILVER_NLP_VERSION,
) -> dict[str, Any] | None:
    purchase_order_id = pick(raw, "Codigo")
    line_item_id = pick(raw, "IDItem")
    if purchase_order_id is None or line_item_id is None:
        return None

    buyer_spec_clean = normalize_text_base(pick(raw, "EspecificacionComprador"))
    supplier_spec_clean = normalize_text_base(pick(raw, "EspecificacionProveedor"))
    combined_text = " ".join(part for part in (buyer_spec_clean, supplier_spec_clean) if part)
    combined_clean = normalize_text_base(combined_text)

    combined_tokens = tokenize_annotation_text(combined_clean)
    combined_keyword_flags = annotation_keyword_flags(combined_tokens)
    combined_domain_tags = semantic_tags_from_flags(combined_keyword_flags)
    buyer_flags = annotation_keyword_flags(tokenize_annotation_text(buyer_spec_clean))
    supplier_flags = annotation_keyword_flags(tokenize_annotation_text(supplier_spec_clean))

    return {
        "purchase_order_id": purchase_order_id,
        "line_item_id": line_item_id,
        "nlp_version": nlp_version,
        "corpus_scope": "purchase_order_line_specs",
        "language_detected": detect_annotation_language(combined_tokens),
        "normalized_tokens_json": combined_tokens,
        "top_ngrams_json": top_ngrams_payload(combined_tokens),
        "buyer_spec_tags_json": buyer_flags,
        "supplier_spec_tags_json": supplier_flags,
        "semantic_category_label": combined_domain_tags[0] if combined_domain_tags else None,
        "tfidf_artifact_ref": tfidf_artifact_ref(
            scope="silver_purchase_order_line",
            entity_id=f"{purchase_order_id}:{line_item_id}",
            text_clean=combined_clean,
            nlp_version=nlp_version,
        ),
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
