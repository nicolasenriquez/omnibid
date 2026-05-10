"""harden mercado publico api operational schema

Revision ID: 202605091540_mp_api_hardening
Revises: 202605081910_mp_api_source
Create Date: 2026-05-09 15:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202605091540_mp_api_hardening"
down_revision: Union[str, None] = "202605081910_mp_api_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipeline_runs", sa.Column("provider", sa.Text(), nullable=True))
    op.add_column("pipeline_runs", sa.Column("run_mode", sa.Text(), nullable=True))
    op.add_column("pipeline_runs", sa.Column("requested_by", sa.Text(), nullable=True))
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "run_parameters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "run_stats_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pipeline_runs_provider_mode_started_at",
        "pipeline_runs",
        ["provider", "run_mode", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_runs_requested_by_started_at",
        "pipeline_runs",
        ["requested_by", "started_at"],
        unique=False,
    )

    op.add_column(
        "api_source_request",
        sa.Column("request_method", sa.Text(), server_default=sa.text("'GET'"), nullable=False),
    )
    op.add_column("api_source_request", sa.Column("request_url_safe", sa.Text(), nullable=True))
    op.add_column(
        "api_source_request",
        sa.Column("cost_units", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column("api_source_request", sa.Column("response_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "api_source_request",
        sa.Column(
            "request_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE api_source_request
            SET rate_limit_day = DATE(requested_at)
            WHERE rate_limit_day IS NULL
            """
        )
    )
    op.alter_column("api_source_request", "rate_limit_day", existing_type=sa.Date(), nullable=False)

    op.drop_constraint("uq_api_source_request_request_hash", "api_source_request", type_="unique")
    op.create_unique_constraint(
        "uq_api_source_request_source_day_hash",
        "api_source_request",
        ["source_system", "rate_limit_day", "request_hash"],
    )
    op.create_index(
        "ix_api_source_request_source_day_requested_at",
        "api_source_request",
        ["source_system", "rate_limit_day", "requested_at"],
        unique=False,
    )

    op.add_column("mercado_publico_notice_snapshot", sa.Column("source_mode", sa.Text(), nullable=True))
    op.add_column(
        "mercado_publico_notice_snapshot",
        sa.Column("payload_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "mercado_publico_notice_snapshot",
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE mercado_publico_notice_snapshot AS snap
            SET payload_sha256 = payload.payload_sha256
            FROM api_source_payload AS payload
            WHERE snap.payload_id = payload.id
            """
        )
    )
    op.alter_column(
        "mercado_publico_notice_snapshot",
        "payload_sha256",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.create_index(
        "ix_mp_notice_snapshot_external_notice_code_snapshot_date",
        "mercado_publico_notice_snapshot",
        ["external_notice_code", "snapshot_date"],
        unique=False,
    )
    op.create_index(
        "ix_mp_notice_snapshot_payload_sha256",
        "mercado_publico_notice_snapshot",
        ["payload_sha256"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_mp_notice_snapshot_external_code_payload_hash",
        "mercado_publico_notice_snapshot",
        ["external_notice_code", "payload_sha256"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_mp_notice_snapshot_external_code_payload_hash",
        "mercado_publico_notice_snapshot",
        type_="unique",
    )
    op.drop_index(
        "ix_mp_notice_snapshot_payload_sha256",
        table_name="mercado_publico_notice_snapshot",
    )
    op.drop_index(
        "ix_mp_notice_snapshot_external_notice_code_snapshot_date",
        table_name="mercado_publico_notice_snapshot",
    )
    op.drop_column("mercado_publico_notice_snapshot", "observed_at")
    op.drop_column("mercado_publico_notice_snapshot", "payload_sha256")
    op.drop_column("mercado_publico_notice_snapshot", "source_mode")

    op.drop_index(
        "ix_api_source_request_source_day_requested_at",
        table_name="api_source_request",
    )
    op.drop_constraint("uq_api_source_request_source_day_hash", "api_source_request", type_="unique")
    op.create_unique_constraint(
        "uq_api_source_request_request_hash",
        "api_source_request",
        ["request_hash"],
    )
    op.alter_column("api_source_request", "rate_limit_day", existing_type=sa.Date(), nullable=True)
    op.drop_column("api_source_request", "request_metadata")
    op.drop_column("api_source_request", "response_hash")
    op.drop_column("api_source_request", "cost_units")
    op.drop_column("api_source_request", "request_url_safe")
    op.drop_column("api_source_request", "request_method")

    op.drop_index("ix_pipeline_runs_requested_by_started_at", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_provider_mode_started_at", table_name="pipeline_runs")
    op.drop_column("pipeline_runs", "run_stats_json")
    op.drop_column("pipeline_runs", "run_parameters_json")
    op.drop_column("pipeline_runs", "requested_by")
    op.drop_column("pipeline_runs", "run_mode")
    op.drop_column("pipeline_runs", "provider")
