from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
import hashlib
import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.models.api_source import MercadoPublicoNoticeSnapshot
from backend.models.normalized import SilverNotice
from backend.normalized.upsert_engine import upsert_rows

MP_API_NOTICE_SILVER_STEP_NAME = "mp_api_notice_silver_refresh"
SILVER_NOTICE_CONFLICT_FIELDS = ["notice_id"]


def _as_naive_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min)


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _resolve_notice_id(snapshot: MercadoPublicoNoticeSnapshot) -> str | None:
    snapshot_any = cast(Any, snapshot)
    notice_id = str(snapshot_any.notice_id or snapshot_any.external_notice_code or "").strip()
    if notice_id == "":
        return None
    return notice_id


def _build_hash_basis(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"source_file_id", "row_hash_sha256", "created_at", "updated_at"}
    }


def build_silver_notice_payload_from_snapshot(
    snapshot: MercadoPublicoNoticeSnapshot,
    *,
    source_file_id: Any,
) -> dict[str, Any] | None:
    snapshot_any = cast(Any, snapshot)
    notice_id = _resolve_notice_id(snapshot)
    if notice_id is None:
        return None

    publication_date = _as_naive_datetime(snapshot_any.publication_date)
    close_date = _as_naive_datetime(snapshot_any.close_date)
    days_publication_to_close: int | None = None
    if publication_date is not None and close_date is not None:
        days_publication_to_close = (close_date - publication_date).days

    payload: dict[str, Any] = {
        "notice_id": notice_id,
        "external_notice_code": str(snapshot_any.external_notice_code),
        "notice_url": None,
        "notice_title": snapshot_any.notice_title,
        "notice_description_raw": None,
        "notice_description_clean": None,
        "procurement_method_name": None,
        "procurement_method_code": None,
        "notice_status_name": snapshot_any.official_status_name,
        "notice_status_code": (
            str(snapshot_any.official_status_code)
            if snapshot_any.official_status_code is not None
            else None
        ),
        "publication_date": publication_date,
        "created_date": None,
        "close_date": close_date,
        "award_date": None,
        "estimated_award_date": None,
        "estimated_amount": snapshot_any.estimated_amount,
        "currency_code": snapshot_any.currency_code,
        "currency_name": None,
        "number_of_bidders_reported": None,
        "complaint_count": None,
        "days_publication_to_close": days_publication_to_close,
        "days_creation_to_close": None,
        "days_close_to_award": None,
        "has_missing_date_chain_flag": True,
        "is_public_tender_flag": False,
        "is_private_tender_flag": False,
        "requires_toma_razon_flag": False,
        "multiple_stages_flag": False,
        "hidden_budget_flag": False,
        "has_extension_flag": False,
        "has_site_visit_flag": False,
        "has_physical_document_delivery_flag": False,
        "notice_line_count": None,
        "notice_bid_count": None,
        "notice_supplier_count": None,
        "notice_selected_bid_count": None,
        "notice_awarded_line_count": None,
        "notice_has_purchase_order_flag": False,
        "notice_purchase_order_count": None,
        "notice_awarded_to_order_conversion_flag": False,
        "source_file_id": source_file_id,
    }
    payload["row_hash_sha256"] = _sha256_json(_build_hash_basis(payload))
    return payload


def select_latest_notice_snapshots(
    session: Session,
    *,
    pipeline_run_id: UUID | None = None,
    window_dates: Sequence[date] | None = None,
) -> list[MercadoPublicoNoticeSnapshot]:
    filters: list[Any] = []
    if pipeline_run_id is not None:
        filters.append(MercadoPublicoNoticeSnapshot.pipeline_run_id == pipeline_run_id)
    if window_dates is not None and len(window_dates) > 0:
        filters.append(MercadoPublicoNoticeSnapshot.snapshot_date.in_(list(window_dates)))
    if not filters:
        raise ValueError("either pipeline_run_id or window_dates is required")

    snapshots = session.execute(
        sa.select(MercadoPublicoNoticeSnapshot)
        .where(*filters)
        .order_by(
            MercadoPublicoNoticeSnapshot.synced_at.desc(),
            MercadoPublicoNoticeSnapshot.id.desc(),
        )
    ).scalars().all()

    latest_by_notice: dict[str, MercadoPublicoNoticeSnapshot] = {}
    for snapshot in snapshots:
        notice_id = _resolve_notice_id(snapshot)
        if notice_id is None:
            continue
        if notice_id in latest_by_notice:
            continue
        latest_by_notice[notice_id] = snapshot

    return [latest_by_notice[key] for key in sorted(latest_by_notice.keys())]


@dataclass(frozen=True)
class MpApiNoticeSilverRefreshSummary:
    notice_candidates: int
    upserted_notices: int


def refresh_silver_notice_from_mp_api_snapshots(
    session: Session,
    *,
    source_file_id: Any,
    pipeline_run_id: UUID | None = None,
    window_dates: Sequence[date] | None = None,
) -> MpApiNoticeSilverRefreshSummary:
    snapshots = select_latest_notice_snapshots(
        session,
        pipeline_run_id=pipeline_run_id,
        window_dates=window_dates,
    )
    payloads = [
        payload
        for payload in (
            build_silver_notice_payload_from_snapshot(snapshot, source_file_id=source_file_id)
            for snapshot in snapshots
        )
        if payload is not None
    ]
    upserted = upsert_rows(session, SilverNotice, payloads, SILVER_NOTICE_CONFLICT_FIELDS)
    return MpApiNoticeSilverRefreshSummary(
        notice_candidates=len(snapshots),
        upserted_notices=upserted,
    )
