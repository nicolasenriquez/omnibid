from __future__ import annotations

from uuid import uuid4

from backend.nlp.annotations import (
    ANNOTATION_DOMAIN_KEYWORDS,
    DEFAULT_SILVER_NLP_VERSION,
    annotation_keyword_flags,
    build_nlp_annotation_bundle,
    build_silver_notice_text_ann_payload,
    detect_annotation_language,
    normalize_annotation_text,
    semantic_tags_from_flags,
    tokenize_annotation_text,
    top_ngrams_payload,
)
from backend.normalized import transform as normalized_transform


def test_nlp_contract_is_loaded_from_versioned_config() -> None:
    assert DEFAULT_SILVER_NLP_VERSION == "silver_nlp_v1"
    assert "maintenance" in ANNOTATION_DOMAIN_KEYWORDS
    assert "soporte" in ANNOTATION_DOMAIN_KEYWORDS["maintenance"]


def test_normalize_annotation_text_collapses_whitespace_and_lowers_case() -> None:
    assert normalize_annotation_text("  Servicio   de Mantención  ") == "servicio de mantencion"


def test_tokenize_annotation_text_applies_deterministic_normalization() -> None:
    assert tokenize_annotation_text("  Licencias de Software y soporte  ") == [
        "licencias",
        "de",
        "software",
        "y",
        "soporte",
    ]


def test_detect_annotation_language_falls_back_to_und_for_short_text() -> None:
    assert detect_annotation_language(["soporte"]) == "und"
    assert detect_annotation_language(["servicio", "tecnico"]) == "es"


def test_annotation_keyword_flags_and_semantic_tags_use_loaded_patterns() -> None:
    flags = annotation_keyword_flags(["software", "soporte"])
    assert flags["it_services"] is True
    assert flags["maintenance"] is True
    assert semantic_tags_from_flags(flags) == ["it_services", "maintenance"]


def test_top_ngrams_payload_is_stable_and_sorted() -> None:
    payload = top_ngrams_payload(["servicio", "tecnico", "servicio"])
    assert payload[0] == {"ngram": "servicio", "count": 2}
    assert payload[1] == {"ngram": "servicio tecnico", "count": 1}


def test_annotation_bundle_uses_the_silver_contract() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "Descripcion": "Servicio de mantencion y soporte de software",
        "Descripcion linea Adquisicion": "Mantencion de red y soporte tecnico",
        "Codigoitem": "IT-1",
        "Codigo": "OC-1",
        "IDItem": "1",
        "EspecificacionComprador": "Mantencion de red",
        "EspecificacionProveedor": "Soporte tecnico",
    }
    bundle = build_nlp_annotation_bundle(raw, uuid4(), "h" * 64)
    assert bundle["notice_text_ann"] is not None
    assert bundle["notice_line_text_ann"] is not None
    assert bundle["purchase_order_line_text_ann"] is not None

    notice_payload = build_silver_notice_text_ann_payload(raw, uuid4(), "h" * 64)
    assert notice_payload is not None
    assert notice_payload["semantic_category_label"] in {"it_services", "maintenance"}


def test_normalized_transform_exports_nlp_annotation_contract_builders() -> None:
    assert (
        normalized_transform.build_silver_notice_text_ann_payload
        is build_silver_notice_text_ann_payload
    )
