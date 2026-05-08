from __future__ import annotations

import hashlib
from typing import Any

from backend.nlp.normalization import normalize_annotation_text

EMBEDDING_ARTIFACT_PREFIX = "embedding://"
FORBIDDEN_SILVER_EMBEDDING_FIELDS = (
    "embedding",
    "embeddings",
    "embedding_vector",
    "dense_vector",
    "sentence_embedding",
)


def build_embedding_artifact_ref(
    *,
    scope: str,
    entity_id: str,
    text: str | None,
    model_name: str,
    embedding_version: str,
) -> str | None:
    text_clean = normalize_annotation_text(text)
    if text_clean is None:
        return None
    payload = f"{scope}|{entity_id}|{model_name}|{embedding_version}|{text_clean}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return (
        f"{EMBEDDING_ARTIFACT_PREFIX}{scope}/{model_name}/"
        f"{embedding_version}/{digest}"
    )


def build_downstream_embedding_record(
    *,
    scope: str,
    entity_id: str,
    text: str | None,
    model_name: str,
    embedding_version: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    artifact_ref = build_embedding_artifact_ref(
        scope=scope,
        entity_id=entity_id,
        text=text,
        model_name=model_name,
        embedding_version=embedding_version,
    )
    if artifact_ref is None:
        return None
    return {
        "artifact_ref": artifact_ref,
        "scope": scope,
        "entity_id": entity_id,
        "model_name": model_name,
        "embedding_version": embedding_version,
        "metadata": metadata or {},
    }
