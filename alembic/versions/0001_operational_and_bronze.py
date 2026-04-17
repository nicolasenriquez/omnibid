"""create operational and bronze tables

Revision ID: 0001_operational_and_bronze
Revises:
Create Date: 2026-04-16 19:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_operational_and_bronze"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "source_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'registered'"), nullable=False),
        sa.Column("source_meta", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_hash_sha256"),
    )
    op.create_index("ix_source_files_dataset_type", "source_files", ["dataset_type"], unique=False)

    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_key", sa.Text(), nullable=False),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'running'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_key"),
    )
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"], unique=False)

    op.create_table(
        "pipeline_run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'running'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_in", sa.BigInteger(), nullable=True),
        sa.Column("rows_out", sa.BigInteger(), nullable=True),
        sa.Column("rows_rejected", sa.BigInteger(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_run_steps_run_id", "pipeline_run_steps", ["run_id"], unique=False)

    op.create_table(
        "ingestion_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'started'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_rows", sa.BigInteger(), nullable=True),
        sa.Column("loaded_rows", sa.BigInteger(), nullable=True),
        sa.Column("rejected_rows", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_key"),
    )

    op.create_table(
        "data_quality_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text(), nullable=True),
        sa.Column("issue_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), server_default=sa.text("'warning'"), nullable=False),
        sa.Column("record_ref", sa.Text(), nullable=True),
        sa.Column("column_name", sa.Text(), nullable=True),
        sa.Column("issue_value", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "bronze_licitaciones_raw",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_row_num", sa.BigInteger(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("codigo_externo", sa.Text(), nullable=True),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batches.id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_file_id", "raw_row_num", name="uq_bronze_lic_raw_file_row"),
    )
    op.create_index(
        "ix_bronze_licitaciones_raw_codigo_externo",
        "bronze_licitaciones_raw",
        ["codigo_externo"],
        unique=False,
    )

    op.create_table(
        "bronze_ordenes_compra_raw",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_row_num", sa.BigInteger(), nullable=False),
        sa.Column("codigo_oc", sa.Text(), nullable=True),
        sa.Column("codigo_licitacion", sa.Text(), nullable=True),
        sa.Column("id_item", sa.Text(), nullable=True),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batches.id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_file_id", "raw_row_num", name="uq_bronze_oc_raw_file_row"),
    )
    op.create_index(
        "ix_bronze_ordenes_compra_raw_codigo_oc",
        "bronze_ordenes_compra_raw",
        ["codigo_oc"],
        unique=False,
    )
    op.create_index(
        "ix_bronze_ordenes_compra_raw_codigo_licitacion",
        "bronze_ordenes_compra_raw",
        ["codigo_licitacion"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bronze_ordenes_compra_raw_codigo_licitacion", table_name="bronze_ordenes_compra_raw")
    op.drop_index("ix_bronze_ordenes_compra_raw_codigo_oc", table_name="bronze_ordenes_compra_raw")
    op.drop_table("bronze_ordenes_compra_raw")

    op.drop_index("ix_bronze_licitaciones_raw_codigo_externo", table_name="bronze_licitaciones_raw")
    op.drop_table("bronze_licitaciones_raw")

    op.drop_table("data_quality_issues")
    op.drop_table("ingestion_batches")

    op.drop_index("ix_pipeline_run_steps_run_id", table_name="pipeline_run_steps")
    op.drop_table("pipeline_run_steps")

    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")

    op.drop_index("ix_source_files_dataset_type", table_name="source_files")
    op.drop_table("source_files")
