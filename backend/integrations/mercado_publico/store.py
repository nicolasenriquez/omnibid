from __future__ import annotations

from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.integrations.mercado_publico.schemas import LicitacionNotice
from backend.models.api_source import ApiSourcePayload, ApiSourceRequest, MercadoPublicoNoticeSnapshot


SECRET_KEYS = {"ticket"}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_request_params(params: Mapping[str, Any]) -> dict[str, Any]:
    canonical: dict[str, Any] = {}
    for key, value in sorted(params.items(), key=lambda item: item[0]):
        if key.lower() in SECRET_KEYS:
            continue
        canonical[key] = value
    return canonical


def _json_compatible_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_compatible(item) for key, item in value.items()}


def _json_compatible_sequence(value: Sequence[Any]) -> list[Any]:
    return [_json_compatible(item) for item in value]


def _json_compatible(value: Any) -> Any:
    if isinstance(value, Mapping):
        mapping = cast(dict[str, Any], value)
        return {str(key): _json_compatible(item) for key, item in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast(list[Any], value)
        return [_json_compatible(item) for item in sequence]
    if isinstance(value, (date, datetime, Decimal, UUID)):
        return str(value)
    return value


def compute_request_hash(params: Mapping[str, Any]) -> str:
    return _sha256(_json_dumps(canonical_request_params(params)))


def compute_payload_hash(payload: Mapping[str, Any]) -> str:
    return _sha256(_json_dumps(payload))


@dataclass(frozen=True)
class PersistedNoticeBatch:
    request_id: UUID
    payload_id: UUID
    request_hash: str
    payload_sha256: str
    notices_seen: int
    notices_skipped_missing_external_notice_code: int
    snapshots_upserted: int
    snapshots_inserted: int
    snapshots_updated: int


@contextmanager
def _transaction(session: Session) -> Generator[None, None, None]:
    if session.in_transaction():
        yield
        return
    with session.begin():
        yield


def _uuid_from_any(value: Any, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    text = str(value or "").strip()
    if text == "":
        raise ValueError(f"{field_name} is required")
    return UUID(text)


def persist_notice_batch(
    session: Session,
    *,
    pipeline_run_id: UUID,
    endpoint_name: str,
    resource_type: str,
    resource_key: str | None,
    request_params: Mapping[str, Any],
    payload: Mapping[str, Any],
    notices: Sequence[LicitacionNotice],
    source_system: str = "mercado_publico",
    requested_at: datetime | None = None,
    completed_at: datetime | None = None,
    http_status: int = 200,
) -> PersistedNoticeBatch:
    request_hash = compute_request_hash(request_params)
    payload_sha256 = compute_payload_hash(payload)
    now = _utc_now()
    effective_requested_at = requested_at or now
    effective_completed_at = completed_at or now
    observed_keys = sorted(str(key) for key in payload.keys())

    with _transaction(session):
        request = session.execute(
            select(ApiSourceRequest).where(ApiSourceRequest.request_hash == request_hash)
        ).scalar_one_or_none()
        if request is None:
            request = ApiSourceRequest(
                pipeline_run_id=pipeline_run_id,
                source_system=source_system,
                endpoint_name=endpoint_name,
                resource_type=resource_type,
                resource_key=resource_key,
                request_params_json=_json_compatible(canonical_request_params(request_params)),
                request_hash=request_hash,
                requested_at=effective_requested_at,
                rate_limit_day=effective_requested_at.date(),
            )
            session.add(request)
            session.flush()

        payload_row = session.execute(
            select(ApiSourcePayload).where(ApiSourcePayload.payload_sha256 == payload_sha256)
        ).scalar_one_or_none()
        if payload_row is None:
            payload_row = ApiSourcePayload(
                pipeline_run_id=pipeline_run_id,
                source_system=source_system,
                endpoint_name=endpoint_name,
                resource_type=resource_type,
                resource_key=resource_key,
                fetched_at=effective_completed_at,
                payload_json=_json_compatible(payload),
                payload_sha256=payload_sha256,
                source_fecha_creacion=_resolve_payload_source_date(payload.get("FechaCreacion")),
                source_count=_resolve_payload_count(payload.get("Cantidad")),
                schema_observed_keys=observed_keys,
            )
            session.add(payload_row)
            session.flush()

        request_id = _uuid_from_any(request.id, field_name="api_source_request.id")
        payload_id = _uuid_from_any(payload_row.id, field_name="api_source_payload.id")
        session.execute(
            sa.update(ApiSourceRequest)
            .where(ApiSourceRequest.id == request_id)
            .values(
                pipeline_run_id=pipeline_run_id,
                source_system=source_system,
                endpoint_name=endpoint_name,
                resource_type=resource_type,
                resource_key=resource_key,
                request_params_json=canonical_request_params(request_params),
                requested_at=effective_requested_at,
                completed_at=effective_completed_at,
                http_status=http_status,
                success=True,
                error_type=None,
                error_message=None,
                response_payload_id=payload_id,
            )
        )

        notices_seen = len(notices)
        notices_skipped_missing_external_notice_code = 0
        snapshots_upserted = 0
        snapshots_inserted = 0
        snapshots_updated = 0
        for notice in notices:
            external_notice_code = (notice.external_notice_code or "").strip()
            if external_notice_code == "":
                notices_skipped_missing_external_notice_code += 1
                continue
            snapshot_values = {
                "pipeline_run_id": pipeline_run_id,
                "request_id": request_id,
                "payload_id": payload_id,
                "endpoint_name": endpoint_name,
                "resource_key": resource_key,
                "notice_id": external_notice_code,
                "external_notice_code": external_notice_code,
                "notice_title": notice.title,
                "official_status_code": notice.official_status_code,
                "official_status_name": notice.official_status_name,
                "publication_date": notice.publication_date,
                "close_date": notice.close_date,
                "buyer_org_code": notice.buyer_org_code,
                "buyer_org_name": notice.buyer_org_name,
                "buyer_unit_code": notice.buyer_unit_code,
                "buyer_unit_name": notice.buyer_unit_name,
                "currency_code": notice.currency_code,
                "estimated_amount": _decimal_or_none(notice.estimated_amount),
                "snapshot_date": notice.publication_date or effective_completed_at.date(),
                "synced_at": effective_completed_at,
            }
            insert_stmt = (
                pg_insert(MercadoPublicoNoticeSnapshot)
                .values(snapshot_values)
                .on_conflict_do_nothing(index_elements=["payload_id", "external_notice_code"])
                .returning(sa.literal(1))
            )
            inserted_marker = session.execute(insert_stmt).scalar_one_or_none()
            if inserted_marker == 1:
                snapshots_inserted += 1
                snapshots_upserted += 1
                continue

            update_values = {
                "pipeline_run_id": pipeline_run_id,
                "request_id": request_id,
                "endpoint_name": endpoint_name,
                "resource_key": resource_key,
                "notice_id": external_notice_code,
                "notice_title": notice.title,
                "official_status_code": notice.official_status_code,
                "official_status_name": notice.official_status_name,
                "publication_date": notice.publication_date,
                "close_date": notice.close_date,
                "buyer_org_code": notice.buyer_org_code,
                "buyer_org_name": notice.buyer_org_name,
                "buyer_unit_code": notice.buyer_unit_code,
                "buyer_unit_name": notice.buyer_unit_name,
                "currency_code": notice.currency_code,
                "estimated_amount": _decimal_or_none(notice.estimated_amount),
                "snapshot_date": notice.publication_date or effective_completed_at.date(),
                "synced_at": effective_completed_at,
            }
            updated_marker = session.execute(
                sa.update(MercadoPublicoNoticeSnapshot)
                .where(
                    MercadoPublicoNoticeSnapshot.payload_id == payload_id,
                    MercadoPublicoNoticeSnapshot.external_notice_code == external_notice_code,
                )
                .values(**update_values)
                .returning(sa.literal(1))
            )
            if updated_marker.scalar_one_or_none() != 1:
                raise RuntimeError(
                    "unexpected update rowcount for mercado_publico_notice_snapshot conflict row"
                )
            snapshots_updated += 1
            snapshots_upserted += 1

        session.flush()

    return PersistedNoticeBatch(
        request_id=request_id,
        payload_id=payload_id,
        request_hash=request_hash,
        payload_sha256=payload_sha256,
        notices_seen=notices_seen,
        notices_skipped_missing_external_notice_code=notices_skipped_missing_external_notice_code,
        snapshots_upserted=snapshots_upserted,
        snapshots_inserted=snapshots_inserted,
        snapshots_updated=snapshots_updated,
    )


def _resolve_payload_source_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized == "":
            return None
        if len(normalized) == 10 and normalized[4] == "-" and normalized[7] == "-":
            return date.fromisoformat(normalized)
    return None


def _resolve_payload_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized == "":
            return None
        if normalized.isdigit():
            return int(normalized)
    return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
