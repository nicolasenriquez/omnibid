import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.db.base import Base


class SourceFile(Base):
    __tablename__ = "source_files"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    dataset_type = sa.Column(sa.Text, nullable=False)
    file_name = sa.Column(sa.Text, nullable=False)
    file_path = sa.Column(sa.Text, nullable=False)
    file_size_bytes = sa.Column(sa.BigInteger, nullable=False)
    file_hash_sha256 = sa.Column(sa.String(64), nullable=False, unique=True)
    source_modified_at = sa.Column(sa.DateTime(timezone=True))
    registered_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    status = sa.Column(sa.Text, nullable=False, server_default=sa.text("'registered'"))
    source_meta = sa.Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))

    __table_args__ = (
        sa.Index("ix_source_files_dataset_type", "dataset_type"),
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    run_key = sa.Column(sa.Text, nullable=False, unique=True)
    dataset_type = sa.Column(sa.Text, nullable=False)
    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"))
    status = sa.Column(sa.Text, nullable=False, server_default=sa.text("'running'"))
    started_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    finished_at = sa.Column(sa.DateTime(timezone=True))
    config = sa.Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    error_summary = sa.Column(sa.Text)

    __table_args__ = (
        sa.Index("ix_pipeline_runs_status", "status"),
    )


class PipelineRunStep(Base):
    __tablename__ = "pipeline_run_steps"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    run_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False)
    step_name = sa.Column(sa.Text, nullable=False)
    status = sa.Column(sa.Text, nullable=False, server_default=sa.text("'running'"))
    started_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    finished_at = sa.Column(sa.DateTime(timezone=True))
    rows_in = sa.Column(sa.BigInteger)
    rows_out = sa.Column(sa.BigInteger)
    rows_rejected = sa.Column(sa.BigInteger)
    error_details = sa.Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))

    __table_args__ = (
        sa.Index("ix_pipeline_run_steps_run_id", "run_id"),
    )


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    batch_key = sa.Column(sa.Text, nullable=False, unique=True)
    status = sa.Column(sa.Text, nullable=False, server_default=sa.text("'started'"))
    started_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    finished_at = sa.Column(sa.DateTime(timezone=True))
    total_rows = sa.Column(sa.BigInteger)
    loaded_rows = sa.Column(sa.BigInteger)
    rejected_rows = sa.Column(sa.BigInteger)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    run_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False)
    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"))
    dataset_type = sa.Column(sa.Text, nullable=False)
    table_name = sa.Column(sa.Text)
    issue_type = sa.Column(sa.Text, nullable=False)
    severity = sa.Column(sa.Text, nullable=False, server_default=sa.text("'warning'"))
    record_ref = sa.Column(sa.Text)
    column_name = sa.Column(sa.Text)
    issue_value = sa.Column(sa.Text)
    details = sa.Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
