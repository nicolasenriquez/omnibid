from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from backend.pipeline.shared.cleaning import is_licitacion_elegible, normalize_text_base, normalize_tipo_adquisicion

DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
)

NUMERIC_20_6_MAX_ABS = Decimal("99999999999999.999999")

BID_SUBMISSION_SIGNAL_COLUMNS: tuple[str, ...] = (
    "Nombre de la Oferta",
    "Estado Oferta",
    "FechaEnvioOferta",
)


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
            raw_value = cast(Any, raw.get(key))
            if raw_value is not None:
                if isinstance(raw_value, dict):
                    # Sanitize corrupted dict values to str to prevent SQLAlchemy 'can't adapt type' error
                    value = clean_raw_value(str(cast(Any, raw_value)))
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
