from __future__ import annotations

from backend.nlp.embeddings import (
    EMBEDDING_ARTIFACT_PREFIX,
    build_downstream_embedding_record,
    build_embedding_artifact_ref,
)


def test_build_embedding_artifact_ref_is_deterministic_and_downstream_scoped() -> None:
    first = build_embedding_artifact_ref(
        scope="silver_notice",
        entity_id="N-1",
        text="Servicio de soporte tecnico",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_version="emb_v1",
    )
    second = build_embedding_artifact_ref(
        scope="silver_notice",
        entity_id="N-1",
        text="Servicio de soporte tecnico",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_version="emb_v1",
    )
    assert first is not None
    assert first == second
    assert first.startswith(EMBEDDING_ARTIFACT_PREFIX)


def test_build_downstream_embedding_record_returns_artifact_only_payload() -> None:
    record = build_downstream_embedding_record(
        scope="silver_notice",
        entity_id="N-1",
        text="Servicio de soporte tecnico",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_version="emb_v1",
        metadata={"source": "test"},
    )
    assert record is not None
    assert "artifact_ref" in record
    assert "embedding_vector" not in record
    assert "score" not in record
