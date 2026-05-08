from backend.nlp.annotations import (
    ANNOTATION_DOMAIN_KEYWORDS,
    DEFAULT_SILVER_NLP_VERSION,
    MAX_ANNOTATION_NGRAMS,
    MAX_ANNOTATION_TOKENS,
    annotation_keyword_flags,
    build_nlp_annotation_bundle,
    build_silver_notice_line_text_ann_payload,
    build_silver_notice_text_ann_payload,
    build_silver_purchase_order_line_text_ann_payload,
    detect_annotation_language,
    semantic_tags_from_flags,
    tokenize_annotation_text,
    top_ngrams_payload,
)
from backend.nlp.artifacts import row_hash_sha256, tfidf_artifact_ref
from backend.nlp.config import NLPContractConfig, get_nlp_contract_config, load_nlp_contract_config
from backend.nlp.embeddings import (
    EMBEDDING_ARTIFACT_PREFIX,
    FORBIDDEN_SILVER_EMBEDDING_FIELDS,
    build_downstream_embedding_record,
    build_embedding_artifact_ref,
)
from backend.nlp.normalization import normalize_annotation_text
from backend.nlp.runtime import (
    DOCUMENTED_SOURCE_PROFILES,
    IMPLEMENTED_SOURCE_PROFILE,
    normalize_source_profile,
    validate_nlp_runtime_contract,
)

__all__ = [
    "ANNOTATION_DOMAIN_KEYWORDS",
    "DEFAULT_SILVER_NLP_VERSION",
    "DOCUMENTED_SOURCE_PROFILES",
    "EMBEDDING_ARTIFACT_PREFIX",
    "FORBIDDEN_SILVER_EMBEDDING_FIELDS",
    "IMPLEMENTED_SOURCE_PROFILE",
    "MAX_ANNOTATION_NGRAMS",
    "MAX_ANNOTATION_TOKENS",
    "NLPContractConfig",
    "annotation_keyword_flags",
    "build_nlp_annotation_bundle",
    "build_downstream_embedding_record",
    "build_embedding_artifact_ref",
    "build_silver_notice_line_text_ann_payload",
    "build_silver_notice_text_ann_payload",
    "build_silver_purchase_order_line_text_ann_payload",
    "detect_annotation_language",
    "get_nlp_contract_config",
    "load_nlp_contract_config",
    "normalize_annotation_text",
    "normalize_source_profile",
    "row_hash_sha256",
    "semantic_tags_from_flags",
    "tfidf_artifact_ref",
    "tokenize_annotation_text",
    "top_ngrams_payload",
    "validate_nlp_runtime_contract",
]
