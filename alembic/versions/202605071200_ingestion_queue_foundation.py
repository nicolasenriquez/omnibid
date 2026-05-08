"""add ingestion queue foundation tables

Revision ID: 202605071200_ing_queue
Revises: 202605021830_source_hash_idx
Create Date: 2026-05-07 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202605071200_ing_queue"
down_revision: Union[str, None] = "202605021830_source_hash_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("payload_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checkpoint_meta", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'staged'"), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cleanup_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_checkpoints_status_created_at",
        "source_checkpoints",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_source_checkpoints_payload_hash",
        "source_checkpoints",
        ["payload_hash_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_source_checkpoints_source_file_id",
        "source_checkpoints",
        ["source_file_id"],
        unique=False,
    )

    op.create_table(
        "pipeline_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("source_checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("2"), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("max_attempts >= 1", name="ck_pipeline_jobs_max_attempts_gte_1"),
        sa.CheckConstraint("attempts >= 0", name="ck_pipeline_jobs_attempts_gte_0"),
        sa.ForeignKeyConstraint(["source_checkpoint_id"], ["source_checkpoints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_jobs_pick",
        "pipeline_jobs",
        ["status", "available_at", "priority", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_jobs_locked",
        "pipeline_jobs",
        ["locked_at"],
        unique=False,
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "ix_pipeline_jobs_type_status",
        "pipeline_jobs",
        ["job_type", "status"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_jobs_source_checkpoint_id",
        "pipeline_jobs",
        ["source_checkpoint_id"],
        unique=False,
    )

    op.create_table(
        "ingestion_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("api_call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("raw_min_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_max_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_inserted_rows", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("raw_duplicate_rows", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'started'"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["pipeline_jobs.id"]),
        sa.ForeignKeyConstraint(["source_checkpoint_id"], ["source_checkpoints.id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_units_job_id", "ingestion_units", ["job_id"], unique=False)
    op.create_index(
        "ix_ingestion_units_source_checkpoint_id",
        "ingestion_units",
        ["source_checkpoint_id"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_units_status_created_at",
        "ingestion_units",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_units_status_created_at", table_name="ingestion_units")
    op.drop_index("ix_ingestion_units_source_checkpoint_id", table_name="ingestion_units")
    op.drop_index("ix_ingestion_units_job_id", table_name="ingestion_units")
    op.drop_table("ingestion_units")

    op.drop_index("ix_pipeline_jobs_source_checkpoint_id", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_type_status", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_locked", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_pick", table_name="pipeline_jobs")
    op.drop_table("pipeline_jobs")

    op.drop_index("ix_source_checkpoints_source_file_id", table_name="source_checkpoints")
    op.drop_index("ix_source_checkpoints_payload_hash", table_name="source_checkpoints")
    op.drop_index("ix_source_checkpoints_status_created_at", table_name="source_checkpoints")
    op.drop_table("source_checkpoints")
