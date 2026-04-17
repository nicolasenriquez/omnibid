from __future__ import annotations

import re
import unicodedata


def normalize_text_base(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip().lower()
    if text == "":
        return None

    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_tipo_adquisicion(value: str | None) -> str | None:
    text = normalize_text_base(value)
    if text is None:
        return None

    def _cleanup_utm(match: re.Match[str]) -> str:
        # Convert values like 5.000 or 5,000 -> 5000 only in UTM context.
        return re.sub(r"[\.,]", "", match.group(1))

    return re.sub(r"\b(\d{1,3}(?:[\.,]\d{3})+)(?=\s*utm\b)", _cleanup_utm, text)


def is_licitacion_elegible(tipo_adquisicion: str | None) -> bool:
    """Business rule MVP: public/private, non-service, below 100 UTM."""
    text = normalize_tipo_adquisicion(tipo_adquisicion)
    if text is None:
        return False

    is_public_or_private = ("licitacion publica" in text) or ("licitacion privada" in text)
    is_service = (
        "servicios personales especializados" in text
        or "licitacion de servicios" in text
    )
    is_under_100 = "menor a 100 utm" in text

    return is_public_or_private and (not is_service) and is_under_100
