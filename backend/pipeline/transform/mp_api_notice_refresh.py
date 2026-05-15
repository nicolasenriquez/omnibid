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
from backend.pipeline.shared.cleaning import normalize_text_base
from backend.pipeline.transform.upsert_engine import upsert_rows

MP_API_NOTICE_SILVER_STEP_NAME = "mp_api_notice_silver_refresh"
SILVER_NOTICE_CONFLICT_FIELDS = ["notice_id"]
DETAIL_SOURCE_MODE = "detail-by-codigo"

OFFICIAL_STATE_BY_CODE: dict[int, tuple[str, str]] = {
    5: ("Publicada", "publicada"),
    6: ("Cerrada", "cerrada"),
    7: ("Desierta", "desierta"),
    8: ("Adjudicada", "adjudicada"),
    18: ("Revocada", "revocada"),
    19: ("Suspendida", "suspendida"),
}
OFFICIAL_STATE_BY_NAME: dict[str, tuple[int, str]] = {
    normalize_text_base(name) or "": (code, canonical)
    for code, (name, canonical) in OFFICIAL_STATE_BY_CODE.items()
}


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


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _derive_official_state(
    *,
    status_code_raw: Any,
    status_name_raw: Any,
) -> tuple[int | None, str | None, str | None]:
    status_code = _as_int(status_code_raw)
    status_name = _as_text(status_name_raw)

    if status_code is not None and status_code in OFFICIAL_STATE_BY_CODE:
        mapped_name, canonical = OFFICIAL_STATE_BY_CODE[status_code]
        return status_code, status_name or mapped_name, canonical

    status_norm = normalize_text_base(status_name)
    mapped_by_name = OFFICIAL_STATE_BY_NAME.get(status_norm or "")
    if mapped_by_name is not None:
        mapped_code, canonical = mapped_by_name
        return status_code or mapped_code, status_name, canonical

    return status_code, status_name, status_norm


def _derive_data_source_kind(*, source_mode: Any, state_canonical: str | None) -> str:
    mode = normalize_text_base(_as_text(source_mode))
    if mode == DETAIL_SOURCE_MODE:
        return "api_detail"
    if state_canonical == "publicada":
        return "api_publicada"
    if mode in {"active-discovery", "rolling-window"}:
        return "api_historical"
    return "api_unknown"


def _derive_availability_context(*, source_mode: Any, state_canonical: str | None) -> str:
    mode = normalize_text_base(_as_text(source_mode))
    if state_canonical == "publicada":
        if mode == DETAIL_SOURCE_MODE:
            return "current_publicada_detail"
        return "current_publicada_discovery"
    return "historical_full_cycle"


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
    created_date = _as_naive_datetime(snapshot_any.created_date)
    close_date = _as_naive_datetime(snapshot_any.close_date)
    award_date = _as_naive_datetime(snapshot_any.award_date)
    estimated_award_date = _as_naive_datetime(snapshot_any.estimated_award_date)

    official_state_code, official_state_name, official_state_canonical = _derive_official_state(
        status_code_raw=snapshot_any.official_status_code,
        status_name_raw=snapshot_any.official_status_name,
    )
    source_mode = _as_text(snapshot_any.source_mode)
    data_source_kind = _derive_data_source_kind(
        source_mode=source_mode,
        state_canonical=official_state_canonical,
    )
    availability_context = _derive_availability_context(
        source_mode=source_mode,
        state_canonical=official_state_canonical,
    )

    tipo_norm = normalize_text_base(_as_text(snapshot_any.tipo)) or ""
    visibility_norm = normalize_text_base(_as_text(snapshot_any.visibility_amount)) or ""
    description_raw = _as_text(snapshot_any.description)
    description_clean = normalize_text_base(description_raw)

    days_publication_to_close: int | None = None
    if publication_date is not None and close_date is not None:
        days_publication_to_close = (close_date - publication_date).days
    days_creation_to_close: int | None = None
    if created_date is not None and close_date is not None:
        days_creation_to_close = (close_date - created_date).days
    days_close_to_award: int | None = None
    if close_date is not None and award_date is not None:
        days_close_to_award = (award_date - close_date).days

    payload: dict[str, Any] = {
        "notice_id": notice_id,
        "external_notice_code": str(snapshot_any.external_notice_code),
        "notice_url": None,
        "notice_title": snapshot_any.notice_title,
        "notice_description_raw": description_raw,
        "notice_description_clean": description_clean,
        "procurement_method_name": _as_text(snapshot_any.tipo),
        "procurement_method_code": _as_text(snapshot_any.codigo_tipo),
        "notice_status_name": official_state_name,
        "notice_status_code": str(official_state_code) if official_state_code is not None else None,
        "mp_estado_codigo": official_state_code,
        "mp_estado_nombre": official_state_name,
        "mp_estado_canonical": official_state_canonical,
        "data_source_kind": data_source_kind,
        "availability_context": availability_context,
        "publication_date": publication_date,
        "created_date": created_date,
        "close_date": close_date,
        "award_date": award_date,
        "estimated_award_date": estimated_award_date,
        "estimated_amount": snapshot_any.estimated_amount,
        "currency_code": snapshot_any.currency_code,
        "currency_name": None,
        "number_of_bidders_reported": None,
        "complaint_count": _as_int(snapshot_any.claim_count),
        "days_publication_to_close": days_publication_to_close,
        "days_creation_to_close": days_creation_to_close,
        "days_close_to_award": days_close_to_award,
        "has_missing_date_chain_flag": (
            publication_date is None or close_date is None or award_date is None
        ),
        "is_public_tender_flag": "publica" in tipo_norm,
        "is_private_tender_flag": "privada" in tipo_norm,
        "requires_toma_razon_flag": False,
        "multiple_stages_flag": False,
        "hidden_budget_flag": visibility_norm in {"0", "no", "oculto", "reservado"},
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
