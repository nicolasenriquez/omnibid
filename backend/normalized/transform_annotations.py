from __future__ import annotations

from collections import Counter
import hashlib
import re
from typing import Any

from backend.normalized.transform_common import pick
from backend.shared.cleaning import normalize_text_base

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
