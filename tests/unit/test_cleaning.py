from backend.shared.cleaning import (
    is_licitacion_elegible,
    normalize_text_base,
    normalize_tipo_adquisicion,
)


def test_normalize_text_base_removes_accents_and_normalizes_spaces() -> None:
    assert normalize_text_base("  Región   Metropolitana de  SANTIAGO ") == "region metropolitana de santiago"


def test_normalize_tipo_adquisicion_cleans_utm_thousands_separator() -> None:
    value = "Licitación Pública Mayor a 5.000 UTM (LR)"
    assert normalize_tipo_adquisicion(value) == "licitacion publica mayor a 5000 utm (lr)"


def test_is_licitacion_elegible_true_for_public_under_100_non_service() -> None:
    value = "Licitación Pública Menor a 100 UTM (L1)"
    assert is_licitacion_elegible(value) is True


def test_is_licitacion_elegible_false_for_service() -> None:
    value = "Licitación Pública Servicios personales especializados (LS)"
    assert is_licitacion_elegible(value) is False
