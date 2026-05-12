from __future__ import annotations

from collections import Counter
import re
from typing import Any

from backend.nlp.artifacts import tfidf_artifact_ref
from backend.nlp.config import get_nlp_contract_config
from backend.nlp.normalization import normalize_annotation_text
from backend.pipeline.transform.transform_common import pick

_CONTRACT = get_nlp_contract_config()
DEFAULT_SILVER_NLP_VERSION = _CONTRACT.nlp_version
MAX_ANNOTATION_TOKENS = _CONTRACT.max_annotation_tokens
MAX_ANNOTATION_NGRAMS = _CONTRACT.max_annotation_ngrams
ANNOTATION_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = _CONTRACT.domain_keywords
DEFAULT_LANGUAGE = _CONTRACT.default_language
LOW_CONFIDENCE_LANGUAGE_LABEL = _CONTRACT.low_confidence_language_label
MINIMUM_LANGUAGE_TOKENS = _CONTRACT.minimum_language_tokens


def tokenize_annotation_text(text: str | None) -> list[str]:
    normalized = normalize_annotation_text(text)
    if normalized is None:
        return []
    tokens = re.findall(r"[a-z0-9]+", normalized)
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


def detect_annotation_language(tokens: list[str]) -> str:
    if len(tokens) < MINIMUM_LANGUAGE_TOKENS:
        return LOW_CONFIDENCE_LANGUAGE_LABEL
    return DEFAULT_LANGUAGE


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

    description_clean = normalize_annotation_text(pick(raw, "Descripcion"))
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

    line_description_clean = normalize_annotation_text(pick(raw, "Descripcion linea Adquisicion"))
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

    buyer_spec_clean = normalize_annotation_text(pick(raw, "EspecificacionComprador"))
    supplier_spec_clean = normalize_annotation_text(pick(raw, "EspecificacionProveedor"))
    combined_text = " ".join(part for part in (buyer_spec_clean, supplier_spec_clean) if part)
    combined_clean = normalize_annotation_text(combined_text)

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


def build_nlp_annotation_bundle(
    raw: dict[str, Any],
    source_file_id: Any,
    row_hash_sha256: str,
    *,
    nlp_version: str = DEFAULT_SILVER_NLP_VERSION,
) -> dict[str, dict[str, Any] | None]:
    return {
        "notice_text_ann": build_silver_notice_text_ann_payload(
            raw,
            source_file_id,
            row_hash_sha256,
            nlp_version=nlp_version,
        ),
        "notice_line_text_ann": build_silver_notice_line_text_ann_payload(
            raw,
            source_file_id,
            row_hash_sha256,
            nlp_version=nlp_version,
        ),
        "purchase_order_line_text_ann": build_silver_purchase_order_line_text_ann_payload(
            raw,
            source_file_id,
            row_hash_sha256,
            nlp_version=nlp_version,
        ),
    }
