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

from backend.integrations.mercado_publico.errors import MercadoPublicoRateLimitError
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


@dataclass(frozen=True)
class RequestBudgetReservation:
    request_id: UUID
    request_hash: str
    request_date: date
    was_existing: bool


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


def _lock_key_to_bigint(lock_key: str) -> int:
    digest = hashlib.sha256(lock_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False) - (1 << 63)


def _sum_daily_cost_units(
    session: Session,
    *,
    source_system: str,
    request_date: date,
) -> int:
    summed = session.execute(
        select(sa.func.coalesce(sa.func.sum(ApiSourceRequest.cost_units), 0)).where(
            ApiSourceRequest.source_system == source_system,
            ApiSourceRequest.rate_limit_day == request_date,
        )
    ).scalar_one()
    return int(summed or 0)


def reserve_request_budget(
    session: Session,
    *,
    pipeline_run_id: UUID,
    source_system: str,
    endpoint_name: str,
    resource_type: str,
    resource_key: str | None,
    request_params: Mapping[str, Any],
    request_url_safe: str | None,
    daily_limit: int,
    request_method: str = "GET",
    cost_units: int = 1,
    requested_at: datetime | None = None,
    request_metadata: Mapping[str, Any] | None = None,
) -> RequestBudgetReservation:
    if daily_limit < 1:
        raise ValueError("daily_limit must be >= 1")
    if cost_units < 1:
        raise ValueError("cost_units must be >= 1")
    effective_requested_at = requested_at or _utc_now()
    request_date = effective_requested_at.date()
    request_hash = compute_request_hash(request_params)
    canonical_params = _json_compatible(canonical_request_params(request_params))
    metadata_payload = _json_compatible(dict(request_metadata or {}))

    lock_key = f"mercado_publico:budget:{source_system}:{request_date.isoformat()}"
    lock_token = _lock_key_to_bigint(lock_key)

    with _transaction(session):
        session.execute(sa.text("SELECT pg_advisory_xact_lock(:lock_token)"), {"lock_token": lock_token})

        existing = session.execute(
            select(ApiSourceRequest).where(
                ApiSourceRequest.source_system == source_system,
                ApiSourceRequest.rate_limit_day == request_date,
                ApiSourceRequest.request_hash == request_hash,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return RequestBudgetReservation(
                request_id=_uuid_from_any(existing.id, field_name="api_source_request.id"),
                request_hash=request_hash,
                request_date=request_date,
                was_existing=True,
            )

        used_units = _sum_daily_cost_units(
            session,
            source_system=source_system,
            request_date=request_date,
        )
        if used_units + cost_units > daily_limit:
            raise MercadoPublicoRateLimitError(
                "daily request budget exhausted: "
                f"source_system={source_system} date={request_date.isoformat()} "
                f"used={used_units} requested={cost_units} limit={daily_limit}"
            )

        pending_request = ApiSourceRequest(
            pipeline_run_id=pipeline_run_id,
            source_system=source_system,
            endpoint_name=endpoint_name,
            resource_type=resource_type,
            resource_key=resource_key,
            request_method=request_method.upper() if request_method.strip() != "" else "GET",
            request_url_safe=request_url_safe,
            request_params_json=canonical_params,
            request_hash=request_hash,
            requested_at=effective_requested_at,
            success=False,
            error_type="pending",
            error_message=None,
            cost_units=cost_units,
            response_hash=None,
            request_metadata=metadata_payload,
            rate_limit_day=request_date,
        )
        session.add(pending_request)
        session.flush()

        return RequestBudgetReservation(
            request_id=_uuid_from_any(pending_request.id, field_name="api_source_request.id"),
            request_hash=request_hash,
            request_date=request_date,
            was_existing=False,
        )


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
    source_mode: str | None = None,
    request_url_safe: str | None = None,
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
            select(ApiSourceRequest).where(
                ApiSourceRequest.source_system == source_system,
                ApiSourceRequest.rate_limit_day == effective_requested_at.date(),
                ApiSourceRequest.request_hash == request_hash,
            )
        ).scalar_one_or_none()
        if request is None:
            request = ApiSourceRequest(
                pipeline_run_id=pipeline_run_id,
                source_system=source_system,
                endpoint_name=endpoint_name,
                resource_type=resource_type,
                resource_key=resource_key,
                request_method="GET",
                request_url_safe=request_url_safe,
                request_params_json=_json_compatible(canonical_request_params(request_params)),
                request_hash=request_hash,
                requested_at=effective_requested_at,
                rate_limit_day=effective_requested_at.date(),
                cost_units=1,
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
                request_method="GET",
                request_url_safe=request_url_safe,
                request_params_json=canonical_request_params(request_params),
                requested_at=effective_requested_at,
                completed_at=effective_completed_at,
                http_status=http_status,
                success=True,
                error_type=None,
                error_message=None,
                cost_units=1,
                response_hash=payload_sha256,
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
                "payload_sha256": payload_sha256,
                "endpoint_name": endpoint_name,
                "source_mode": source_mode,
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
                "observed_at": effective_completed_at,
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
                "source_mode": source_mode,
                "resource_key": resource_key,
                "notice_id": external_notice_code,
                "payload_sha256": payload_sha256,
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
                "observed_at": effective_completed_at,
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
