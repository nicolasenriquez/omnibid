from __future__ import annotations

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.models.normalized import SilverNotice, SilverNoticeTextAnn
from backend.models.operational import SourceFile
from backend.nlp.annotations import build_silver_notice_text_ann_payload
from backend.pipeline.transform.upsert_engine import upsert_rows


def _prepare_silver_notice_text_ann_schema(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    Base.metadata.create_all(
        engine,
        tables=[
            SourceFile.__table__,
            SilverNotice.__table__,
            SilverNoticeTextAnn.__table__,
        ],
    )


@pytest.mark.integration
def test_silver_notice_text_ann_upsert_writes_reference_only_payload() -> None:
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    assert test_database_url, "TEST_DATABASE_URL must be set for integration tests"

    engine = create_engine(test_database_url, pool_pre_ping=True, future=True)
    _prepare_silver_notice_text_ann_schema(engine)

    source_file_id = uuid4()
    notice_id = "N-INTEGRATION-1"
    row_hash_sha256 = "h" * 64
    payload = build_silver_notice_text_ann_payload(
        {
            "CodigoExterno": notice_id,
            "Descripcion": "Servicio de mantencion y soporte de software",
        },
        source_file_id=source_file_id,
        row_hash_sha256=row_hash_sha256,
    )
    assert payload is not None

    with Session(engine, future=True) as session:
        session.execute(
            sa.insert(SourceFile).values(
                id=source_file_id,
                dataset_type="licitacion",
                file_name="integration.jsonl",
                file_path="/tmp/integration.jsonl",
                file_size_bytes=1,
                file_hash_sha256="f" * 64,
            )
        )
        session.execute(
            sa.insert(SilverNotice).values(
                notice_id=notice_id,
                source_file_id=source_file_id,
                row_hash_sha256="n" * 64,
            )
        )

        upsert_rows(session, SilverNoticeTextAnn, [payload], ["notice_id", "nlp_version"])

        row = session.execute(
            sa.select(SilverNoticeTextAnn).where(
                SilverNoticeTextAnn.notice_id == notice_id,
                SilverNoticeTextAnn.nlp_version == payload["nlp_version"],
            )
        ).scalar_one()

    assert row.notice_id == notice_id
    assert row.corpus_scope == "notice_description"
    assert row.language_detected == "es"
    assert isinstance(row.normalized_tokens_json, list)
    assert row.tfidf_artifact_ref is not None
    assert row.tfidf_artifact_ref.startswith("tfidf://silver_notice/")
    assert row.row_hash_sha256 == row_hash_sha256
    assert row.semantic_category_label in {"maintenance", "it_services"}
