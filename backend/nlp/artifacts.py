from __future__ import annotations

import hashlib
import json
from typing import Any


def row_hash_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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
