from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.models.api_source import ApiSourcePayload, MercadoPublicoNoticeItemSnapshot, MercadoPublicoNoticeSnapshot
from backend.models.normalized import (
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedSupplier,
    SilverAwardOutcome,
    SilverBidSubmission,
    SilverBuyingOrg,
    SilverCategoryRef,
    SilverContractingUnit,
    SilverNotice,
    SilverNoticeLine,
    SilverSupplier,
    SilverSupplierParticipation,
)
from backend.pipeline.load.postprocess import (
    reconcile_silver_notice_purchase_order_links,
    refresh_silver_notice_and_line_enrichments,
    refresh_silver_purchase_order_enrichments,
)
from backend.normalized.transform import (
    build_licitacion_item_payload,
    build_licitacion_payload,
    build_oferta_payload,
    build_silver_award_outcome_payload,
    build_silver_bid_submission_payload,
    build_silver_buying_org_payload,
    build_silver_category_ref_payload,
    build_silver_contracting_unit_payload,
    build_silver_notice_line_payload,
    build_silver_notice_payload,
    build_silver_supplier_participation_payload,
    build_silver_supplier_payload,
    build_supplier_domain_payload,
    resolve_supplier_identity_key,
)
from backend.pipeline.transform.upsert_engine import upsert_rows

LICITACIONES_CONFLICT_FIELDS = ["codigo_externo"]
LICITACION_ITEMS_CONFLICT_FIELDS = ["codigo_externo", "codigo_item"]
OFERTAS_CONFLICT_FIELDS = ["oferta_key_sha256"]
SUPPLIERS_CONFLICT_FIELDS = ["supplier_key"]
SILVER_NOTICE_CONFLICT_FIELDS = ["notice_id"]
SILVER_NOTICE_LINE_CONFLICT_FIELDS = ["notice_id", "item_code"]
SILVER_BID_SUBMISSION_CONFLICT_FIELDS = ["bid_submission_id"]
SILVER_AWARD_OUTCOME_CONFLICT_FIELDS = ["award_outcome_id"]
SILVER_BUYING_ORG_CONFLICT_FIELDS = ["buying_org_id"]
SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS = ["contracting_unit_id"]
SILVER_SUPPLIER_CONFLICT_FIELDS = ["supplier_id"]
SILVER_CATEGORY_REF_CONFLICT_FIELDS = ["category_ref_id"]
SILVER_SUPPLIER_PARTICIPATION_CONFLICT_FIELDS = ["supplier_id", "notice_id"]

DETAIL_MODE = "detail-by-codigo"

SNAPSHOT_ROW_FIELD_MAP: dict[str, str] = {
    "CodigoExterno": "external_notice_code",
    "Nombre": "notice_title",
    "CodigoEstado": "official_status_code",
    "Estado": "official_status_name",
    "FechaPublicacion": "publication_date",
    "FechaCierre": "close_date",
    "FechaCreacion": "created_date",
    "FechaAdjudicacion": "award_date",
    "FechaEstimadaAdjudicacion": "estimated_award_date",
    "Descripcion": "description",
    "CodigoOrganismo": "buyer_org_code",
    "NombreOrganismo": "buyer_org_name",
    "CodigoUnidad": "buyer_unit_code",
    "NombreUnidad": "buyer_unit_name",
    "DireccionUnidad": "buyer_unit_address",
    "ComunaUnidad": "buyer_unit_commune",
    "RegionUnidad": "buyer_unit_region",
    "Moneda": "currency_code",
    "MontoEstimado": "estimated_amount",
    "Tipo": "tipo",
    "CodigoTipo": "codigo_tipo",
    "TipoConvocatoria": "tipo_convocatoria",
    "CantidadReclamos": "claim_count",
    "FuenteFinanciamiento": "funding_source",
    "VisibilidadMonto": "visibility_amount",
}


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _select_latest_snapshots_by_notice(
    session: Session,
    *,
    pipeline_run_id: UUID | None,
    window_dates: Sequence[date] | None,
) -> dict[str, MercadoPublicoNoticeSnapshot]:
    filters = _scope_filters(pipeline_run_id=pipeline_run_id, window_dates=window_dates)
    source_mode_priority = sa.case(
        (MercadoPublicoNoticeSnapshot.source_mode == DETAIL_MODE, 0),
        (MercadoPublicoNoticeSnapshot.source_mode == "rolling-window", 1),
        else_=2,
    )
    snapshots = session.execute(
        sa.select(MercadoPublicoNoticeSnapshot)
        .where(*filters)
        .order_by(
            source_mode_priority.asc(),
            MercadoPublicoNoticeSnapshot.synced_at.desc(),
            MercadoPublicoNoticeSnapshot.id.desc(),
        )
    ).scalars().all()
    by_code: dict[str, MercadoPublicoNoticeSnapshot] = {}
    for snapshot in snapshots:
        code = _text_or_none(snapshot.external_notice_code)
        if code is None or code in by_code:
            continue
        by_code[code] = snapshot
    return by_code


def _merge_raw_row_with_snapshot(
    raw_row: Mapping[str, Any],
    snapshot: MercadoPublicoNoticeSnapshot | None,
) -> dict[str, Any]:
    merged = dict(raw_row)
    if snapshot is None:
        return merged
    snap_any = cast(Any, snapshot)
    for row_key, snapshot_attr in SNAPSHOT_ROW_FIELD_MAP.items():
        if not _is_missing_value(merged.get(row_key)):
            continue
        value = getattr(snap_any, snapshot_attr, None)
        if _is_missing_value(value):
            continue
        merged[row_key] = value
    if _is_missing_value(merged.get("SourceMode")):
        merged["SourceMode"] = _text_or_none(getattr(snap_any, "source_mode", None))
    if _is_missing_value(merged.get("Codigo")):
        merged["Codigo"] = _text_or_none(getattr(snap_any, "notice_id", None))
    return merged


def _flatten_items_from_row(raw_row: Mapping[str, Any]) -> list[dict[str, Any]]:
    items_container = _as_dict(raw_row.get("Items"))
    if items_container is None:
        return []
    listed_raw = items_container.get("Listado")
    if not isinstance(listed_raw, Sequence) or isinstance(listed_raw, (str, bytes, bytearray)):
        return []

    flattened_rows: list[dict[str, Any]] = []
    for item_raw in cast(Sequence[object], listed_raw):
        item = _as_dict(item_raw)
        if item is None:
            continue
        item_row = dict(raw_row)
        item_correlative = _as_int(item.get("Correlativo"))
        item_product_code = _text_or_none(item.get("CodigoProducto"))
        item_code = str(item_correlative) if item_correlative is not None else item_product_code
        if item_code is None:
            continue
        item_row["Codigoitem"] = item_code
        item_row["CodigoItem"] = item_code
        item_row["Correlativo"] = str(item_correlative) if item_correlative is not None else None
        item_row["CodigoProductoONU"] = item_product_code
        item_row["codigoCategoria"] = _text_or_none(item.get("CodigoCategoria"))
        item_row["CodigoCategoria"] = _text_or_none(item.get("CodigoCategoria"))
        item_row["Categoria"] = _text_or_none(item.get("Categoria"))
        item_row["Rubro1"] = _text_or_none(item.get("Categoria"))
        item_row["Nombre producto genrico"] = _text_or_none(item.get("NombreProducto"))
        item_row["NombreProductoGenerico"] = _text_or_none(item.get("NombreProducto"))
        item_row["Nombre linea Adquisicion"] = _text_or_none(item.get("NombreProducto"))
        item_row["Descripcion linea Adquisicion"] = _text_or_none(item.get("Descripcion"))
        item_row["UnidadMedida"] = _text_or_none(item.get("UnidadMedida"))
        item_row["Cantidad"] = item.get("Cantidad")
        flattened_rows.append(item_row)
    return flattened_rows


@dataclass(frozen=True)
class MpApiDetailCandidateSummary:
    notice_candidates: int
    detail_candidates: int
    selected_codes: tuple[str, ...]


@dataclass(frozen=True)
class MpApiCanonicalizationSummary:
    payload_rows_seen: int
    payload_rows_used: int
    notice_candidates: int
    upserted_notices: int
    upserted_normalized_licitaciones: int
    upserted_normalized_licitacion_items: int
    upserted_normalized_ofertas: int
    upserted_normalized_suppliers: int
    upserted_silver_notice: int
    upserted_silver_notice_line: int
    upserted_silver_bid_submission: int
    upserted_silver_award_outcome: int
    upserted_silver_buying_org: int
    upserted_silver_contracting_unit: int
    upserted_silver_supplier: int
    upserted_silver_category_ref: int
    upserted_silver_supplier_participation: int


@dataclass(frozen=True)
class MpApiSilverPostprocessSummary:
    notice_purchase_order_links_inserted: int


@dataclass(frozen=True)
class _ScopedPayloadRow:
    payload_sha256: str
    row_index: int
    raw_row: dict[str, Any]
    mode_rank: int
    fetched_at: datetime | None


def _scope_filters(
    *,
    pipeline_run_id: UUID | None,
    window_dates: Sequence[date] | None,
) -> list[Any]:
    filters: list[Any] = []
    if pipeline_run_id is not None:
        filters.append(MercadoPublicoNoticeSnapshot.pipeline_run_id == pipeline_run_id)
    if window_dates is not None and len(window_dates) > 0:
        filters.append(MercadoPublicoNoticeSnapshot.snapshot_date.in_(list(window_dates)))
    if not filters:
        raise ValueError("either pipeline_run_id or window_dates is required")
    return filters


def _mode_rank(source_mode: str | None) -> int:
    return 2 if str(source_mode or "").strip() == DETAIL_MODE else 1


def _row_hash(*, payload_sha256: str, row_index: int, raw_row: Mapping[str, Any]) -> str:
    basis = {
        "payload_sha256": payload_sha256,
        "row_index": row_index,
        "raw_row": raw_row,
    }
    encoded = json.dumps(basis, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _as_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in cast(Mapping[str, Any], value).items()}
    return None


def select_detail_enrichment_candidates(
    session: Session,
    *,
    target_date: date,
    pipeline_run_id: UUID | None = None,
    window_dates: Sequence[date] | None = None,
    backfill_interval_days: int = 7,
    max_candidates: int | None = None,
) -> MpApiDetailCandidateSummary:
    if backfill_interval_days < 1:
        raise ValueError("backfill_interval_days must be >= 1")
    if max_candidates is not None and max_candidates < 1:
        raise ValueError("max_candidates must be >= 1")

    filters = _scope_filters(pipeline_run_id=pipeline_run_id, window_dates=window_dates)
    scoped_codes = sorted(
        {
            str(code).strip()
            for code in session.execute(
                sa.select(MercadoPublicoNoticeSnapshot.external_notice_code).where(*filters)
            ).scalars()
            if str(code or "").strip() != ""
        }
    )
    if not scoped_codes:
        return MpApiDetailCandidateSummary(
            notice_candidates=0,
            detail_candidates=0,
            selected_codes=(),
        )

    freshness_rows = session.execute(
        sa.select(
            MercadoPublicoNoticeSnapshot.external_notice_code,
            sa.func.max(MercadoPublicoNoticeSnapshot.synced_at),
        )
        .where(
            MercadoPublicoNoticeSnapshot.external_notice_code.in_(scoped_codes),
            MercadoPublicoNoticeSnapshot.source_mode == DETAIL_MODE,
        )
        .group_by(MercadoPublicoNoticeSnapshot.external_notice_code)
    ).all()
    latest_detail_by_code = {
        str(code): cast(datetime | None, max_synced)
        for code, max_synced in freshness_rows
        if str(code or "").strip() != ""
    }

    close_date_rows = session.execute(
        sa.select(
            MercadoPublicoNoticeSnapshot.external_notice_code,
            sa.func.max(SilverNotice.close_date),
        )
        .select_from(MercadoPublicoNoticeSnapshot)
        .outerjoin(SilverNotice, SilverNotice.notice_id == MercadoPublicoNoticeSnapshot.external_notice_code)
        .where(
            *filters,
            MercadoPublicoNoticeSnapshot.external_notice_code.in_(scoped_codes),
        )
        .group_by(MercadoPublicoNoticeSnapshot.external_notice_code)
    ).all()
    latest_close_by_code = {
        str(code): cast(datetime | None, max_close)
        for code, max_close in close_date_rows
        if str(code or "").strip() != ""
    }

    cutoff_day = target_date - timedelta(days=backfill_interval_days)
    open_window_end = target_date + timedelta(days=7)
    candidate_rows: list[tuple[int, datetime | None, datetime | None, str]] = []
    for code in scoped_codes:
        latest_detail_synced_at = latest_detail_by_code.get(code)
        latest_close_date = latest_close_by_code.get(code)
        close_day = latest_close_date.date() if latest_close_date is not None else None
        is_open_or_closing_soon = close_day is not None and target_date < close_day <= open_window_end
        is_stale = latest_detail_synced_at is None or latest_detail_synced_at.date() <= cutoff_day
        if not is_open_or_closing_soon and not is_stale:
            continue

        priority = 0 if is_open_or_closing_soon else 1
        candidate_rows.append(
            (
                priority,
                latest_close_date,
                latest_detail_synced_at,
                code,
            )
        )

    candidate_rows.sort(
        key=lambda item: (
            item[0],
            item[1] or datetime.max,
            item[2] or datetime.min,
            item[3],
        )
    )
    detail_candidates = [code for *_rest, code in candidate_rows]
    selected = detail_candidates if max_candidates is None else detail_candidates[:max_candidates]
    return MpApiDetailCandidateSummary(
        notice_candidates=len(scoped_codes),
        detail_candidates=len(detail_candidates),
        selected_codes=tuple(selected),
    )


def _select_scoped_payload_rows(
    session: Session,
    *,
    pipeline_run_id: UUID | None,
    window_dates: Sequence[date] | None,
) -> list[_ScopedPayloadRow]:
    filters = _scope_filters(pipeline_run_id=pipeline_run_id, window_dates=window_dates)
    payload_scope_rows = session.execute(
        sa.select(
            MercadoPublicoNoticeSnapshot.payload_id,
            sa.func.max(MercadoPublicoNoticeSnapshot.synced_at),
            sa.func.max(
                sa.case(
                    (MercadoPublicoNoticeSnapshot.source_mode == DETAIL_MODE, 2),
                    else_=1,
                )
            ),
        )
        .where(*filters)
        .group_by(MercadoPublicoNoticeSnapshot.payload_id)
    ).all()
    if not payload_scope_rows:
        return []

    payload_scope: list[tuple[UUID, datetime | None, int]] = []
    payload_ids: list[UUID] = []
    for payload_id_raw, max_synced_at_raw, mode_rank_raw in payload_scope_rows:
        if not isinstance(payload_id_raw, UUID):
            continue
        payload_id = payload_id_raw
        payload_ids.append(payload_id)
        payload_scope.append(
            (
                payload_id,
                cast(datetime | None, max_synced_at_raw),
                int(mode_rank_raw or 1),
            )
        )
    if not payload_ids:
        return []

    payload_rows = session.execute(
        sa.select(ApiSourcePayload).where(ApiSourcePayload.id.in_(payload_ids))
    ).scalars().all()
    payload_by_id = {cast(UUID, payload.id): payload for payload in payload_rows if isinstance(payload.id, UUID)}

    scoped_rows: list[_ScopedPayloadRow] = []
    for payload_id, max_synced_at, mode_rank in sorted(
        payload_scope,
        key=lambda item: (item[2], item[1] or datetime.min, str(item[0])),
    ):
        payload_row = payload_by_id.get(payload_id)
        if payload_row is None:
            continue
        payload_json = _as_dict(payload_row.payload_json)
        if payload_json is None:
            continue
        listed_rows_raw = payload_json.get("Listado")
        if not isinstance(listed_rows_raw, Sequence) or isinstance(listed_rows_raw, (str, bytes, bytearray)):
            continue
        listed_rows = cast(Sequence[object], listed_rows_raw)
        payload_sha256 = str(payload_row.payload_sha256 or "")
        for row_index, listed_row_raw in enumerate(listed_rows):
            listed_row = _as_dict(listed_row_raw)
            if listed_row is None:
                continue
            scoped_rows.append(
                _ScopedPayloadRow(
                    payload_sha256=payload_sha256,
                    row_index=row_index,
                    raw_row=listed_row,
                    mode_rank=mode_rank,
                    fetched_at=cast(datetime | None, payload_row.fetched_at) or max_synced_at,
                )
            )
    return scoped_rows


def canonicalize_mp_api_payloads_to_read_model(
    session: Session,
    *,
    source_file_id: Any,
    pipeline_run_id: UUID | None = None,
    window_dates: Sequence[date] | None = None,
    include_normalized: bool = True,
) -> MpApiCanonicalizationSummary:
    latest_snapshot_by_code = _select_latest_snapshots_by_notice(
        session,
        pipeline_run_id=pipeline_run_id,
        window_dates=window_dates,
    )
    scoped_rows = _select_scoped_payload_rows(
        session,
        pipeline_run_id=pipeline_run_id,
        window_dates=window_dates,
    )

    normalized_licitaciones_rows: list[dict[str, Any]] = []
    normalized_licitacion_items_rows: list[dict[str, Any]] = []
    normalized_ofertas_rows: list[dict[str, Any]] = []
    normalized_suppliers_rows: list[dict[str, Any]] = []

    silver_notice_rows: list[dict[str, Any]] = []
    silver_notice_line_rows: list[dict[str, Any]] = []
    silver_bid_submission_rows: list[dict[str, Any]] = []
    silver_award_outcome_rows: list[dict[str, Any]] = []
    silver_buying_org_rows: list[dict[str, Any]] = []
    silver_contracting_unit_rows: list[dict[str, Any]] = []
    silver_supplier_rows: list[dict[str, Any]] = []
    silver_category_ref_rows: list[dict[str, Any]] = []
    silver_supplier_participation_rows: list[dict[str, Any]] = []

    payload_rows_used = 0
    notice_candidates: set[str] = set()
    for scoped_row in scoped_rows:
        notice_code = _text_or_none(scoped_row.raw_row.get("CodigoExterno"))
        enriched_row = _merge_raw_row_with_snapshot(
            scoped_row.raw_row,
            latest_snapshot_by_code.get(notice_code or ""),
        )
        expanded_rows: list[dict[str, Any]] = [enriched_row]
        if _is_missing_value(enriched_row.get("Codigoitem")) and _is_missing_value(enriched_row.get("CodigoItem")):
            expanded_rows.extend(_flatten_items_from_row(enriched_row))

        row_had_payload = False
        for synthetic_index, raw_row in enumerate(expanded_rows):
            row_hash_sha256 = _row_hash(
                payload_sha256=scoped_row.payload_sha256,
                row_index=(scoped_row.row_index * 1000) + synthetic_index,
                raw_row=raw_row,
            )

            licitacion_payload = build_licitacion_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                row_hash_sha256=row_hash_sha256,
            )
            if licitacion_payload is not None:
                normalized_licitaciones_rows.append(licitacion_payload)
                row_had_payload = True

            licitacion_item_payload = build_licitacion_item_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                row_hash_sha256=row_hash_sha256,
            )
            if licitacion_item_payload is not None:
                normalized_licitacion_items_rows.append(licitacion_item_payload)
                row_had_payload = True

            oferta_payload = build_oferta_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                row_hash_sha256=row_hash_sha256,
            )
            if oferta_payload is not None:
                oferta_payload["supplier_key"] = resolve_supplier_identity_key(raw_row)
                normalized_ofertas_rows.append(oferta_payload)
                row_had_payload = True

                supplier_payload = build_supplier_domain_payload(
                    raw=raw_row,
                    source_file_id=source_file_id,
                )
                if supplier_payload is not None:
                    normalized_suppliers_rows.append(supplier_payload)

            silver_notice_payload = build_silver_notice_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                row_hash_sha256=row_hash_sha256,
            )
            if silver_notice_payload is not None:
                silver_notice_rows.append(silver_notice_payload)
                notice_candidates.add(str(silver_notice_payload.get("notice_id")))
                row_had_payload = True

            silver_notice_line_payload = build_silver_notice_line_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                row_hash_sha256=row_hash_sha256,
            )
            if silver_notice_line_payload is not None:
                silver_notice_line_rows.append(silver_notice_line_payload)
                row_had_payload = True

            silver_bid_submission_payload = build_silver_bid_submission_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                row_hash_sha256=row_hash_sha256,
            )
            if silver_bid_submission_payload is not None:
                silver_bid_submission_rows.append(silver_bid_submission_payload)
                row_had_payload = True

            silver_award_outcome_payload = build_silver_award_outcome_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                row_hash_sha256=row_hash_sha256,
            )
            if silver_award_outcome_payload is not None:
                silver_award_outcome_rows.append(silver_award_outcome_payload)
                row_had_payload = True

            silver_buying_org_payload = build_silver_buying_org_payload(
                raw=raw_row,
                source_file_id=source_file_id,
            )
            if silver_buying_org_payload is not None:
                silver_buying_org_rows.append(silver_buying_org_payload)

            silver_contracting_unit_payload = build_silver_contracting_unit_payload(
                raw=raw_row,
                source_file_id=source_file_id,
            )
            if silver_contracting_unit_payload is not None:
                silver_contracting_unit_rows.append(silver_contracting_unit_payload)

            silver_supplier_payload = build_silver_supplier_payload(
                raw=raw_row,
                source_file_id=source_file_id,
            )
            if silver_supplier_payload is not None:
                silver_supplier_rows.append(silver_supplier_payload)

            silver_category_ref_payload = build_silver_category_ref_payload(
                raw=raw_row,
                source_file_id=source_file_id,
            )
            if silver_category_ref_payload is not None:
                silver_category_ref_rows.append(silver_category_ref_payload)

            silver_supplier_participation_payload = build_silver_supplier_participation_payload(
                raw=raw_row,
                source_file_id=source_file_id,
                bid_submission_payload=silver_bid_submission_payload,
                award_outcome_payload=silver_award_outcome_payload,
            )
            if silver_supplier_participation_payload is not None:
                silver_supplier_participation_rows.append(silver_supplier_participation_payload)

        if row_had_payload:
            payload_rows_used += 1

    upserted_normalized_licitaciones = 0
    upserted_normalized_licitacion_items = 0
    if include_normalized:
        upserted_normalized_licitaciones = upsert_rows(
            session,
            NormalizedLicitacion,
            normalized_licitaciones_rows,
            LICITACIONES_CONFLICT_FIELDS,
        )
        upserted_normalized_licitacion_items = upsert_rows(
            session,
            NormalizedLicitacionItem,
            normalized_licitacion_items_rows,
            LICITACION_ITEMS_CONFLICT_FIELDS,
        )
    upserted_normalized_ofertas = upsert_rows(
        session,
        NormalizedOferta,
        normalized_ofertas_rows,
        OFERTAS_CONFLICT_FIELDS,
    )
    upserted_normalized_suppliers = upsert_rows(
        session,
        NormalizedSupplier,
        normalized_suppliers_rows,
        SUPPLIERS_CONFLICT_FIELDS,
    )

    upserted_silver_notice = upsert_rows(
        session,
        SilverNotice,
        silver_notice_rows,
        SILVER_NOTICE_CONFLICT_FIELDS,
    )
    upserted_silver_notice_line = upsert_rows(
        session,
        SilverNoticeLine,
        silver_notice_line_rows,
        SILVER_NOTICE_LINE_CONFLICT_FIELDS,
    )
    upserted_silver_bid_submission = upsert_rows(
        session,
        SilverBidSubmission,
        silver_bid_submission_rows,
        SILVER_BID_SUBMISSION_CONFLICT_FIELDS,
    )
    upserted_silver_award_outcome = upsert_rows(
        session,
        SilverAwardOutcome,
        silver_award_outcome_rows,
        SILVER_AWARD_OUTCOME_CONFLICT_FIELDS,
    )
    upserted_silver_buying_org = upsert_rows(
        session,
        SilverBuyingOrg,
        silver_buying_org_rows,
        SILVER_BUYING_ORG_CONFLICT_FIELDS,
    )
    upserted_silver_contracting_unit = upsert_rows(
        session,
        SilverContractingUnit,
        silver_contracting_unit_rows,
        SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS,
    )
    upserted_silver_supplier = upsert_rows(
        session,
        SilverSupplier,
        silver_supplier_rows,
        SILVER_SUPPLIER_CONFLICT_FIELDS,
    )
    upserted_silver_category_ref = upsert_rows(
        session,
        SilverCategoryRef,
        silver_category_ref_rows,
        SILVER_CATEGORY_REF_CONFLICT_FIELDS,
    )
    upserted_silver_supplier_participation = upsert_rows(
        session,
        SilverSupplierParticipation,
        silver_supplier_participation_rows,
        SILVER_SUPPLIER_PARTICIPATION_CONFLICT_FIELDS,
    )

    return MpApiCanonicalizationSummary(
        payload_rows_seen=len(scoped_rows),
        payload_rows_used=payload_rows_used,
        notice_candidates=len(notice_candidates),
        upserted_notices=upserted_silver_notice,
        upserted_normalized_licitaciones=upserted_normalized_licitaciones,
        upserted_normalized_licitacion_items=upserted_normalized_licitacion_items,
        upserted_normalized_ofertas=upserted_normalized_ofertas,
        upserted_normalized_suppliers=upserted_normalized_suppliers,
        upserted_silver_notice=upserted_silver_notice,
        upserted_silver_notice_line=upserted_silver_notice_line,
        upserted_silver_bid_submission=upserted_silver_bid_submission,
        upserted_silver_award_outcome=upserted_silver_award_outcome,
        upserted_silver_buying_org=upserted_silver_buying_org,
        upserted_silver_contracting_unit=upserted_silver_contracting_unit,
        upserted_silver_supplier=upserted_silver_supplier,
        upserted_silver_category_ref=upserted_silver_category_ref,
        upserted_silver_supplier_participation=upserted_silver_supplier_participation,
    )


def _as_naive_datetime(value: date | None) -> datetime | None:
    from datetime import time

    if value is None:
        return None
    return datetime.combine(value, time.min)


def _sha256_json_basis(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text != "" else None


def _stable_item_codigo_fallback(*, codigo_externo: str, item_snapshot: Any) -> str:
    basis = {
        "codigo_externo": codigo_externo,
        "codigo_producto": _strip_or_none(item_snapshot.codigo_producto),
        "codigo_categoria": _strip_or_none(item_snapshot.codigo_categoria),
        "categoria": _strip_or_none(item_snapshot.categoria),
        "nombre_producto": _strip_or_none(item_snapshot.nombre_producto),
        "descripcion": _strip_or_none(item_snapshot.descripcion),
        "unidad_medida": _strip_or_none(item_snapshot.unidad_medida),
        "cantidad": _strip_or_none(item_snapshot.cantidad),
    }
    encoded = json.dumps(basis, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return f"item-{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def build_normalized_licitacion_from_snapshot(
    snapshot: MercadoPublicoNoticeSnapshot,
    *,
    source_file_id: Any,
) -> dict[str, Any] | None:
    snap_any = cast(Any, snapshot)
    codigo_externo = _strip_or_none(snap_any.external_notice_code)
    if codigo_externo is None:
        return None

    codigo = _strip_or_none(snap_any.notice_id) or codigo_externo
    fecha_publicacion = _as_naive_datetime(snap_any.publication_date)
    fecha_cierre = _as_naive_datetime(snap_any.close_date)
    cantidad_dias = None
    if fecha_publicacion is not None and fecha_cierre is not None:
        cantidad_dias = (fecha_cierre - fecha_publicacion).days

    payload: dict[str, Any] = {
        "codigo_externo": codigo_externo,
        "codigo": codigo,
        "nombre": snap_any.notice_title,
        "descripcion": snap_any.description,
        "tipo_adquisicion": snap_any.tipo,
        "tipo_adquisicion_norm": None,
        "codigo_estado": snap_any.official_status_code,
        "estado": snap_any.official_status_name,
        "tipo": snap_any.tipo,
        "tipo_convocatoria": snap_any.tipo_convocatoria,
        "moneda_adquisicion": snap_any.currency_code,
        "visibilidad_monto_raw": snap_any.visibility_amount,
        "monto_estimado": snap_any.estimated_amount,
        "numero_oferentes": None,
        "codigo_organismo": snap_any.buyer_org_code,
        "nombre_organismo": snap_any.buyer_org_name,
        "codigo_unidad": snap_any.buyer_unit_code,
        "nombre_unidad": snap_any.buyer_unit_name,
        "comuna_unidad": snap_any.buyer_unit_commune,
        "region_unidad": snap_any.buyer_unit_region,
        "fecha_publicacion": fecha_publicacion,
        "fecha_cierre": fecha_cierre,
        "fecha_adjudicacion": _as_naive_datetime(snap_any.award_date),
        "fecha_estimada_adjudicacion": _as_naive_datetime(snap_any.estimated_award_date),
        "fecha_inicio": None,
        "fecha_final": None,
        "cantidad_dias_licitacion": snap_any.days_to_close or cantidad_dias,
        "flag_licitacion_publica": False,
        "flag_licitacion_privada": False,
        "flag_licitacion_servicios": False,
        "flag_menos_100_utm": False,
        "is_elegible_mvp": False,
        "source_file_id": source_file_id,
    }
    basis = {
        key: value
        for key, value in payload.items()
        if key not in {"source_file_id", "row_hash_sha256", "created_at", "updated_at"}
    }
    payload["row_hash_sha256"] = _sha256_json_basis(basis)
    return payload


def build_normalized_licitacion_item_from_item_snapshot(
    item_snapshot: MercadoPublicoNoticeItemSnapshot,
    *,
    source_file_id: Any,
) -> dict[str, Any] | None:
    snap_any = cast(Any, item_snapshot)
    codigo_externo = _strip_or_none(snap_any.external_notice_code)
    if codigo_externo is None:
        return None

    correlativo = snap_any.item_correlative
    codigo_producto = _strip_or_none(snap_any.codigo_producto) or ""
    codigo_item = str(correlativo) if correlativo is not None else codigo_producto
    if codigo_item == "":
        codigo_item = _stable_item_codigo_fallback(
            codigo_externo=codigo_externo,
            item_snapshot=snap_any,
        )

    payload: dict[str, Any] = {
        "codigo_externo": codigo_externo,
        "codigo_item": codigo_item,
        "correlativo": str(correlativo) if correlativo is not None else None,
        "codigo_producto_onu": snap_any.codigo_producto,
        "nombre_producto_generico": snap_any.nombre_producto,
        "nombre_linea_adquisicion": snap_any.nombre_producto,
        "descripcion_linea_adquisicion": snap_any.descripcion,
        "unidad_medida": snap_any.unidad_medida,
        "cantidad": parse_decimal(snap_any.cantidad),
        "rubro1": None,
        "rubro2": None,
        "rubro3": None,
        "source_file_id": source_file_id,
    }
    basis = {
        key: value
        for key, value in payload.items()
        if key not in {"source_file_id", "row_hash_sha256", "created_at", "updated_at"}
    }
    payload["row_hash_sha256"] = _sha256_json_basis(basis)
    return payload


def parse_decimal(value: Any) -> Any:
    if value is None:
        return None
    from decimal import Decimal, InvalidOperation

    try:
        return Decimal(str(value))
    except (ValueError, InvalidOperation):
        return None


def canonicalize_api_snapshots_to_normalized(
    session: Session,
    *,
    source_file_id: Any,
    pipeline_run_id: UUID | None = None,
    window_dates: Sequence[date] | None = None,
) -> tuple[int, int]:
    """Map enriched snapshot rows and item snapshots into normalized tables.

    Returns (normalized_licitaciones_count, normalized_items_count).
    Uses the existing anti-degradation upsert engine which applies
    field-level coalesce (prefer non-null incoming, keep existing as fallback).
    """
    filters: list[Any] = []
    if pipeline_run_id is not None:
        filters.append(MercadoPublicoNoticeSnapshot.pipeline_run_id == pipeline_run_id)
    if window_dates is not None and len(window_dates) > 0:
        filters.append(MercadoPublicoNoticeSnapshot.snapshot_date.in_(list(window_dates)))
    if not filters:
        raise ValueError("either pipeline_run_id or window_dates is required")

    source_mode_priority = sa.case(
        (MercadoPublicoNoticeSnapshot.source_mode == DETAIL_MODE, 0),
        (MercadoPublicoNoticeSnapshot.source_mode == "rolling-window", 1),
        else_=2,
    )
    snapshots = session.execute(
        sa.select(MercadoPublicoNoticeSnapshot)
        .where(*filters)
        .order_by(
            source_mode_priority.asc(),
            MercadoPublicoNoticeSnapshot.synced_at.desc(),
            MercadoPublicoNoticeSnapshot.id.desc(),
        )
    ).scalars().all()

    latest_by_code: dict[str, MercadoPublicoNoticeSnapshot] = {}
    for snap in snapshots:
        code = _strip_or_none(snap.external_notice_code)
        if code is None or code in latest_by_code:
            continue
        latest_by_code[code] = snap

    licitacion_payloads: list[dict[str, Any]] = []
    item_payloads: list[dict[str, Any]] = []
    for code in sorted(latest_by_code):
        snap = latest_by_code[code]
        payload = build_normalized_licitacion_from_snapshot(snap, source_file_id=source_file_id)
        if payload is not None:
            licitacion_payloads.append(payload)

        item_snapshots = session.execute(
            sa.select(MercadoPublicoNoticeItemSnapshot).where(
                MercadoPublicoNoticeItemSnapshot.external_notice_code == code,
            ).order_by(
                MercadoPublicoNoticeItemSnapshot.synced_at.desc(),
                MercadoPublicoNoticeItemSnapshot.observed_at.desc(),
                sa.func.coalesce(MercadoPublicoNoticeItemSnapshot.item_correlative, sa.literal(-1)).asc(),
                MercadoPublicoNoticeItemSnapshot.id.asc(),
            )
        ).scalars().all()
        for item_snap in item_snapshots:
            item_payload = build_normalized_licitacion_item_from_item_snapshot(
                item_snap, source_file_id=source_file_id
            )
            if item_payload is not None:
                item_payloads.append(item_payload)

    licitacion_count = upsert_rows(
        session,
        NormalizedLicitacion,
        licitacion_payloads,
        LICITACIONES_CONFLICT_FIELDS,
    )
    item_count = upsert_rows(
        session,
        NormalizedLicitacionItem,
        item_payloads,
        LICITACION_ITEMS_CONFLICT_FIELDS,
    )
    return licitacion_count, item_count


def run_mp_api_silver_postprocess(session: Session) -> MpApiSilverPostprocessSummary:
    refresh_silver_notice_and_line_enrichments(session)
    refresh_silver_purchase_order_enrichments(session)
    inserted_links = reconcile_silver_notice_purchase_order_links(session)
    return MpApiSilverPostprocessSummary(
        notice_purchase_order_links_inserted=inserted_links,
    )
