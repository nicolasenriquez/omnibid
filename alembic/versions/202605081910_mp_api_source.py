"""add mercado publico api source tables

Revision ID: 202605081910_mp_api_source
Revises: 202605071200_ing_queue
Create Date: 2026-05-08 19:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202605081910_mp_api_source"
down_revision: Union[str, None] = "202605071200_ing_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_source_payload",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("endpoint_name", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_key", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("api_version", sa.Text(), nullable=True),
        sa.Column("source_fecha_creacion", sa.Date(), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=True),
        sa.Column("schema_observed_keys", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_sha256", name="uq_api_source_payload_payload_sha256"),
    )
    op.create_index("ix_api_source_payload_pipeline_run_id", "api_source_payload", ["pipeline_run_id"], unique=False)
    op.create_index("ix_api_source_payload_payload_sha256", "api_source_payload", ["payload_sha256"], unique=False)
    op.create_index(
        "ix_api_source_payload_endpoint_fetched_at",
        "api_source_payload",
        ["endpoint_name", "fetched_at"],
        unique=False,
    )

    op.create_table(
        "api_source_request",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("endpoint_name", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_key", sa.Text(), nullable=True),
        sa.Column("request_params_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("response_payload_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("rate_limit_day", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.ForeignKeyConstraint(["response_payload_id"], ["api_source_payload.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_hash", name="uq_api_source_request_request_hash"),
    )
    op.create_index("ix_api_source_request_pipeline_run_id", "api_source_request", ["pipeline_run_id"], unique=False)
    op.create_index("ix_api_source_request_request_hash", "api_source_request", ["request_hash"], unique=False)
    op.create_index(
        "ix_api_source_request_resource",
        "api_source_request",
        ["resource_type", "resource_key"],
        unique=False,
    )

    op.create_table(
        "mercado_publico_notice_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint_name", sa.Text(), nullable=False),
        sa.Column("resource_key", sa.Text(), nullable=True),
        sa.Column("notice_id", sa.Text(), nullable=True),
        sa.Column("external_notice_code", sa.Text(), nullable=False),
        sa.Column("notice_title", sa.Text(), nullable=True),
        sa.Column("official_status_code", sa.Integer(), nullable=True),
        sa.Column("official_status_name", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("close_date", sa.Date(), nullable=True),
        sa.Column("buyer_org_code", sa.Text(), nullable=True),
        sa.Column("buyer_org_name", sa.Text(), nullable=True),
        sa.Column("buyer_unit_code", sa.Text(), nullable=True),
        sa.Column("buyer_unit_name", sa.Text(), nullable=True),
        sa.Column("currency_code", sa.Text(), nullable=True),
        sa.Column("estimated_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["api_source_request.id"]),
        sa.ForeignKeyConstraint(["payload_id"], ["api_source_payload.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_id", "external_notice_code", name="uq_mp_notice_snapshot_payload_notice"),
    )
    op.create_index(
        "ix_mp_notice_snapshot_pipeline_run_id",
        "mercado_publico_notice_snapshot",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_mp_notice_snapshot_snapshot_date",
        "mercado_publico_notice_snapshot",
        ["snapshot_date"],
        unique=False,
    )
    op.create_index(
        "ix_mp_notice_snapshot_external_notice_code",
        "mercado_publico_notice_snapshot",
        ["external_notice_code"],
        unique=False,
    )
    op.create_index(
        "ix_mp_notice_snapshot_status_code",
        "mercado_publico_notice_snapshot",
        ["official_status_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mp_notice_snapshot_status_code", table_name="mercado_publico_notice_snapshot")
    op.drop_index("ix_mp_notice_snapshot_external_notice_code", table_name="mercado_publico_notice_snapshot")
    op.drop_index("ix_mp_notice_snapshot_snapshot_date", table_name="mercado_publico_notice_snapshot")
    op.drop_index("ix_mp_notice_snapshot_pipeline_run_id", table_name="mercado_publico_notice_snapshot")
    op.drop_table("mercado_publico_notice_snapshot")

    op.drop_index("ix_api_source_request_resource", table_name="api_source_request")
    op.drop_index("ix_api_source_request_request_hash", table_name="api_source_request")
    op.drop_index("ix_api_source_request_pipeline_run_id", table_name="api_source_request")
    op.drop_table("api_source_request")

    op.drop_index("ix_api_source_payload_endpoint_fetched_at", table_name="api_source_payload")
    op.drop_index("ix_api_source_payload_payload_sha256", table_name="api_source_payload")
    op.drop_index("ix_api_source_payload_pipeline_run_id", table_name="api_source_payload")
    op.drop_table("api_source_payload")

