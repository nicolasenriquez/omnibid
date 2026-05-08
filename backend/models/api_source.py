from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.db.base import Base


class ApiSourcePayload(Base):
    __tablename__ = "api_source_payload"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    pipeline_run_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False)
    source_system = sa.Column(sa.Text, nullable=False)
    endpoint_name = sa.Column(sa.Text, nullable=False)
    resource_type = sa.Column(sa.Text, nullable=False)
    resource_key = sa.Column(sa.Text)
    fetched_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    payload_json = sa.Column(JSONB, nullable=False)
    payload_sha256 = sa.Column(sa.String(64), nullable=False)
    api_version = sa.Column(sa.Text)
    source_fecha_creacion = sa.Column(sa.Date)
    source_count = sa.Column(sa.Integer)
    schema_observed_keys = sa.Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))

    __table_args__ = (
        sa.Index("ix_api_source_payload_pipeline_run_id", "pipeline_run_id"),
        sa.Index("ix_api_source_payload_payload_sha256", "payload_sha256"),
        sa.Index("ix_api_source_payload_endpoint_fetched_at", "endpoint_name", "fetched_at"),
        sa.UniqueConstraint("payload_sha256", name="uq_api_source_payload_payload_sha256"),
    )


class ApiSourceRequest(Base):
    __tablename__ = "api_source_request"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    pipeline_run_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False)
    source_system = sa.Column(sa.Text, nullable=False)
    endpoint_name = sa.Column(sa.Text, nullable=False)
    resource_type = sa.Column(sa.Text, nullable=False)
    resource_key = sa.Column(sa.Text)
    request_params_json = sa.Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    request_hash = sa.Column(sa.String(64), nullable=False)
    requested_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    completed_at = sa.Column(sa.DateTime(timezone=True))
    http_status = sa.Column(sa.Integer)
    success = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    error_type = sa.Column(sa.Text)
    error_message = sa.Column(sa.Text)
    response_payload_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("api_source_payload.id"))
    cache_hit = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    rate_limit_day = sa.Column(sa.Date)

    __table_args__ = (
        sa.Index("ix_api_source_request_pipeline_run_id", "pipeline_run_id"),
        sa.Index("ix_api_source_request_request_hash", "request_hash"),
        sa.Index("ix_api_source_request_resource", "resource_type", "resource_key"),
        sa.UniqueConstraint("request_hash", name="uq_api_source_request_request_hash"),
    )


class MercadoPublicoNoticeSnapshot(Base):
    __tablename__ = "mercado_publico_notice_snapshot"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    pipeline_run_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False)
    request_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("api_source_request.id"), nullable=False)
    payload_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("api_source_payload.id"), nullable=False)
    endpoint_name = sa.Column(sa.Text, nullable=False)
    resource_key = sa.Column(sa.Text)
    notice_id = sa.Column(sa.Text)
    external_notice_code = sa.Column(sa.Text, nullable=False)
    notice_title = sa.Column(sa.Text)
    official_status_code = sa.Column(sa.Integer)
    official_status_name = sa.Column(sa.Text)
    publication_date = sa.Column(sa.Date)
    close_date = sa.Column(sa.Date)
    buyer_org_code = sa.Column(sa.Text)
    buyer_org_name = sa.Column(sa.Text)
    buyer_unit_code = sa.Column(sa.Text)
    buyer_unit_name = sa.Column(sa.Text)
    currency_code = sa.Column(sa.Text)
    estimated_amount = sa.Column(sa.Numeric(20, 2))
    snapshot_date = sa.Column(sa.Date, nullable=False)
    synced_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_mp_notice_snapshot_pipeline_run_id", "pipeline_run_id"),
        sa.Index("ix_mp_notice_snapshot_snapshot_date", "snapshot_date"),
        sa.Index("ix_mp_notice_snapshot_external_notice_code", "external_notice_code"),
        sa.Index("ix_mp_notice_snapshot_status_code", "official_status_code"),
        sa.UniqueConstraint(
            "payload_id",
            "external_notice_code",
            name="uq_mp_notice_snapshot_payload_notice",
        ),
    )

