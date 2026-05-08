from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.db.base import Base


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    job_type = sa.Column(sa.Text, nullable=False)
    source_kind = sa.Column(sa.Text, nullable=False)
    dataset_type = sa.Column(sa.Text, nullable=False)
    source_checkpoint_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("source_checkpoints.id"),
        nullable=False,
    )
    status = sa.Column(sa.Text, nullable=False, server_default=sa.text("'queued'"))
    priority = sa.Column(sa.Integer, nullable=False, server_default=sa.text("100"))
    payload = sa.Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    attempts = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    max_attempts = sa.Column(sa.Integer, nullable=False, server_default=sa.text("2"))
    available_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    locked_at = sa.Column(sa.DateTime(timezone=True))
    locked_by = sa.Column(sa.Text)
    started_at = sa.Column(sa.DateTime(timezone=True))
    finished_at = sa.Column(sa.DateTime(timezone=True))
    failed_at = sa.Column(sa.DateTime(timezone=True))
    error_message = sa.Column(sa.Text)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index(
            "ix_pipeline_jobs_pick",
            "status",
            "available_at",
            "priority",
            "created_at",
            "id",
        ),
        sa.Index("ix_pipeline_jobs_locked", "locked_at", postgresql_where=sa.text("status = 'running'")),
        sa.Index("ix_pipeline_jobs_type_status", "job_type", "status"),
        sa.Index("ix_pipeline_jobs_source_checkpoint_id", "source_checkpoint_id"),
    )


class IngestionUnit(Base):
    __tablename__ = "ingestion_units"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    job_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("pipeline_jobs.id"), nullable=False)
    source_checkpoint_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_checkpoints.id"), nullable=False)
    source_kind = sa.Column(sa.Text, nullable=False)
    dataset_type = sa.Column(sa.Text, nullable=False)
    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"))
    api_call_id = sa.Column(UUID(as_uuid=True))
    period_start = sa.Column(sa.Date)
    period_end = sa.Column(sa.Date)
    raw_min_id = sa.Column(sa.BigInteger)
    raw_max_id = sa.Column(sa.BigInteger)
    raw_inserted_rows = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))
    raw_duplicate_rows = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))
    status = sa.Column(sa.Text, nullable=False, server_default=sa.text("'started'"))
    metadata_json = sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    finished_at = sa.Column(sa.DateTime(timezone=True))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_ingestion_units_job_id", "job_id"),
        sa.Index("ix_ingestion_units_source_checkpoint_id", "source_checkpoint_id"),
        sa.Index("ix_ingestion_units_status_created_at", "status", "created_at"),
    )
