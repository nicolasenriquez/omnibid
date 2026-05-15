from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.opportunities_contract import (
    OpportunityDetailResponse,
    OpportunityListResponse,
    OpportunitySummaryResponse,
)
from backend.api.deps import get_db
from backend.api.opportunities_query import (
    COUNT_AND_SUMMARY_FILTER_SQL,
    LIST_FILTER_SQL,
    build_opportunities_filter_params,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

OPPORTUNITY_PAGE_SIZE_DEFAULT = 20
OPPORTUNITY_PAGE_SIZE_MAX = 100
OPPORTUNITY_PAGE_MAX = 500

LIST_SQL = sa.text(
    f"""
    with buyer_info as (
        select distinct on (nl.codigo_externo)
            nl.codigo_externo,
            nl.nombre as normalized_title,
            nl.estado as normalized_official_status,
            nl.monto_estimado as normalized_estimated_amount,
            nl.fecha_publicacion as normalized_publication_date,
            nl.fecha_cierre as normalized_close_date,
            nl.nombre_unidad as buyer_name,
            nl.region_unidad as buyer_region,
            nl.comuna_unidad as buyer_commune,
            nl.tipo as normalized_tipo,
            nl.tipo_convocatoria as normalized_tipo_convocatoria,
            nl.visibilidad_monto_raw as normalized_visibility_amount,
            nl.tipo_adquisicion_norm as procurement_method,
            nl.flag_licitacion_publica,
            nl.flag_licitacion_privada,
            nl.flag_licitacion_servicios,
            nl.flag_menos_100_utm,
            coalesce(nullif(nli.rubro1, ''), nullif(nli.rubro2, ''), nullif(nli.rubro3, '')) as primary_category
        from normalized_licitaciones nl
        left join normalized_licitacion_items nli
            on nli.codigo_externo = nl.codigo_externo
    ),
    latest_snapshot as (
        select distinct on (m.external_notice_code)
            m.external_notice_code,
            m.payload_id,
            m.tipo as snapshot_tipo,
            m.codigo_tipo as snapshot_codigo_tipo,
            m.tipo_convocatoria as snapshot_tipo_convocatoria,
            m.funding_source as snapshot_funding_source,
            m.visibility_amount as snapshot_visibility_amount,
            m.claim_count as snapshot_complaint_count,
            m.buyer_unit_region as snapshot_buyer_region,
            m.buyer_unit_commune as snapshot_buyer_commune,
            m.official_status_code as snapshot_mp_estado_codigo,
            m.official_status_name as snapshot_mp_estado_nombre
        from mercado_publico_notice_snapshot m
        order by
            m.external_notice_code,
            case
                when m.source_mode = 'detail-by-codigo' then 0
                when m.source_mode = 'rolling-window' then 1
                else 2
            end asc,
            m.synced_at desc,
            m.id desc
    ),
    latest_payload as (
        select
            ls.external_notice_code,
            nullif(trim(asp.payload_json ->> 'Informada'), '') as informada
        from latest_snapshot ls
        left join api_source_payload asp
            on asp.id = ls.payload_id
    )
    select
        sn.notice_id,
        sn.external_notice_code,
        coalesce(sn.notice_title, bi.normalized_title) as title,
        coalesce(sn.notice_status_name, bi.normalized_official_status) as official_status,
        coalesce(sn.mp_estado_codigo, ls.snapshot_mp_estado_codigo) as mp_estado_codigo,
        coalesce(
            sn.mp_estado_nombre,
            ls.snapshot_mp_estado_nombre,
            sn.notice_status_name,
            bi.normalized_official_status
        ) as mp_estado_nombre,
        coalesce(
            sn.mp_estado_canonical,
            lower(coalesce(ls.snapshot_mp_estado_nombre, sn.notice_status_name, bi.normalized_official_status))
        ) as mp_estado_canonical,
        sn.data_source_kind,
        sn.availability_context,
        coalesce(sn.procurement_method_code, ls.snapshot_codigo_tipo) as codigo_tipo,
        coalesce(sn.procurement_method_name, ls.snapshot_tipo, bi.normalized_tipo) as tipo,
        coalesce(ls.snapshot_tipo_convocatoria, bi.normalized_tipo_convocatoria) as tipo_convocatoria,
        lp.informada,
        coalesce(ls.snapshot_visibility_amount, bi.normalized_visibility_amount) as visibilidad_monto,
        ls.snapshot_funding_source as fuente_financiamiento,
        coalesce(sn.complaint_count, ls.snapshot_complaint_count) as complaint_count,
        coalesce(sn.estimated_amount, bi.normalized_estimated_amount) as estimated_amount,
        sn.currency_code,
        coalesce(sn.publication_date, bi.normalized_publication_date) as publication_date,
        coalesce(sn.close_date, bi.normalized_close_date) as close_date,
        sn.notice_line_count as line_count,
        sn.notice_bid_count as bid_count,
        sn.notice_supplier_count as supplier_count,
        sn.notice_purchase_order_count as purchase_order_count,
        bi.buyer_name,
        coalesce(bi.buyer_region, ls.snapshot_buyer_region) as buyer_region,
        coalesce(bi.buyer_commune, ls.snapshot_buyer_commune) as buyer_commune,
        bi.primary_category,
        case
            when coalesce(sn.is_public_tender_flag, bi.flag_licitacion_publica) then 'public'
            when coalesce(sn.is_private_tender_flag, bi.flag_licitacion_privada) then 'private'
            when coalesce(bi.flag_licitacion_servicios, false) then 'service'
            else null
        end as procurement_type,
        coalesce(bi.flag_menos_100_utm, false) as is_less_than_100_utm,
        case
            when coalesce(sn.close_date, bi.normalized_close_date) is null then null
            else greatest(
                0,
                floor(extract(epoch from (coalesce(sn.close_date, bi.normalized_close_date) - now())) / 86400)
            )::int
        end as days_remaining,
        case
            when lower(coalesce(coalesce(sn.notice_status_name, bi.normalized_official_status), '')) like '%adjudicada%' then 'awarded'
            when lower(coalesce(coalesce(sn.notice_status_name, bi.normalized_official_status), '')) like '%revocada%'
              or lower(coalesce(coalesce(sn.notice_status_name, bi.normalized_official_status), '')) like '%suspendida%' then 'revoked_or_suspended'
            when coalesce(sn.close_date, bi.normalized_close_date) is null then 'unknown'
            when coalesce(sn.close_date, bi.normalized_close_date) < now() then 'closed'
            when coalesce(sn.close_date, bi.normalized_close_date) <= now() + interval '7 days' then 'closing_soon'
            else 'open'
        end as derived_stage
    from silver_notice sn
    left join buyer_info bi on bi.codigo_externo = sn.notice_id
    left join latest_snapshot ls on ls.external_notice_code = sn.notice_id
    left join latest_payload lp on lp.external_notice_code = sn.notice_id
    {LIST_FILTER_SQL}
    order by
        case when :sort_by = 'close_date' and :sort_order = 'asc' then coalesce(sn.close_date, bi.normalized_close_date) end asc nulls last,
        case when :sort_by = 'close_date' and :sort_order = 'desc' then coalesce(sn.close_date, bi.normalized_close_date) end desc nulls last,
        case when :sort_by = 'publication_date' and :sort_order = 'asc' then coalesce(sn.publication_date, bi.normalized_publication_date) end asc nulls last,
        case when :sort_by = 'publication_date' and :sort_order = 'desc' then coalesce(sn.publication_date, bi.normalized_publication_date) end desc nulls last,
        case when :sort_by = 'estimated_amount' and :sort_order = 'asc' then coalesce(sn.estimated_amount, bi.normalized_estimated_amount) end asc nulls last,
        case when :sort_by = 'estimated_amount' and :sort_order = 'desc' then coalesce(sn.estimated_amount, bi.normalized_estimated_amount) end desc nulls last,
        case when :sort_by = 'days_remaining' and :sort_order = 'asc' then coalesce(sn.close_date, bi.normalized_close_date) end asc nulls last,
        case when :sort_by = 'days_remaining' and :sort_order = 'desc' then coalesce(sn.close_date, bi.normalized_close_date) end desc nulls last
    limit :page_size
    offset :offset
    """
)

COUNT_SQL = sa.text(
    f"""
    select count(*) as total
    from silver_notice sn
    left join normalized_licitaciones nl on nl.codigo_externo = sn.notice_id
    {COUNT_AND_SUMMARY_FILTER_SQL}
    """
)

SUMMARY_SQL = sa.text(
    f"""
    select
        count(*) as total_opportunities,
        count(*) filter (where coalesce(sn.close_date, nl.fecha_cierre) is null) as unknown_stage,
        count(*) filter (where coalesce(sn.close_date, nl.fecha_cierre) > now() + interval '7 days') as open,
        count(*) filter (
            where coalesce(sn.close_date, nl.fecha_cierre) > now()
              and coalesce(sn.close_date, nl.fecha_cierre) <= now() + interval '7 days'
        ) as closing_soon,
        count(*) filter (
            where coalesce(sn.close_date, nl.fecha_cierre) <= now()
              and lower(coalesce(coalesce(sn.notice_status_name, nl.estado), '')) not like '%adjudicada%'
              and lower(coalesce(coalesce(sn.notice_status_name, nl.estado), '')) not like '%revocada%'
              and lower(coalesce(coalesce(sn.notice_status_name, nl.estado), '')) not like '%suspendida%'
        ) as closed,
        count(*) filter (where lower(coalesce(coalesce(sn.notice_status_name, nl.estado), '')) like '%adjudicada%') as awarded,
        count(*) filter (
            where lower(coalesce(coalesce(sn.notice_status_name, nl.estado), '')) like '%revocada%'
               or lower(coalesce(coalesce(sn.notice_status_name, nl.estado), '')) like '%suspendida%'
        ) as revoked_or_suspended,
        count(*) filter (
            where coalesce(sn.mp_estado_canonical, lower(nl.estado)) = 'publicada'
        ) as mp_publicada,
        count(*) filter (
            where coalesce(sn.data_source_kind, '') in ('api_publicada', 'api_detail')
        ) as source_publicadas,
        count(*) filter (
            where coalesce(sn.availability_context, '') in ('current_publicada_discovery', 'current_publicada_detail')
        ) as availability_publicadas,
        count(*) filter (where coalesce(sn.estimated_amount, nl.monto_estimado) is not null) as with_estimated_amount,
        coalesce(
            avg(coalesce(sn.estimated_amount, nl.monto_estimado))
            filter (where coalesce(sn.estimated_amount, nl.monto_estimado) is not null),
            0
        ) as avg_estimated_amount,
        coalesce(
            sum(coalesce(sn.estimated_amount, nl.monto_estimado))
            filter (where coalesce(sn.estimated_amount, nl.monto_estimado) is not null),
            0
        ) as total_estimated_amount
    from silver_notice sn
    left join normalized_licitaciones nl on nl.codigo_externo = sn.notice_id
    {COUNT_AND_SUMMARY_FILTER_SQL}
    """
)

DETAIL_SQL = sa.text(
    """
    with buyer_info as (
        select
            nl.codigo_externo,
            nl.nombre as normalized_title,
            nl.descripcion as normalized_description,
            nl.estado as normalized_official_status,
            nl.monto_estimado as normalized_estimated_amount,
            nl.nombre_unidad as buyer_name,
            nl.region_unidad as buyer_region,
            nl.comuna_unidad as buyer_commune,
            nl.codigo_unidad as contracting_unit_code,
            nl.nombre_unidad as contracting_unit_name,
            nl.tipo as normalized_tipo,
            nl.tipo_convocatoria as normalized_tipo_convocatoria,
            nl.visibilidad_monto_raw as normalized_visibility_amount,
            nl.fecha_publicacion as normalized_publication_date,
            nl.fecha_cierre as normalized_close_date,
            nl.fecha_adjudicacion as normalized_award_date,
            nl.fecha_estimada_adjudicacion as normalized_estimated_award_date
        from normalized_licitaciones nl
    ),
    latest_snapshot as (
        select distinct on (m.external_notice_code)
            m.external_notice_code,
            m.payload_id,
            m.tipo as snapshot_tipo,
            m.codigo_tipo as snapshot_codigo_tipo,
            m.tipo_convocatoria as snapshot_tipo_convocatoria,
            m.funding_source as snapshot_funding_source,
            m.visibility_amount as snapshot_visibility_amount,
            m.claim_count as snapshot_complaint_count,
            m.buyer_unit_region as snapshot_buyer_region,
            m.buyer_unit_commune as snapshot_buyer_commune,
            m.official_status_code as snapshot_mp_estado_codigo,
            m.official_status_name as snapshot_mp_estado_nombre
        from mercado_publico_notice_snapshot m
        order by
            m.external_notice_code,
            case
                when m.source_mode = 'detail-by-codigo' then 0
                when m.source_mode = 'rolling-window' then 1
                else 2
            end asc,
            m.synced_at desc,
            m.id desc
    ),
    latest_payload as (
        select
            ls.external_notice_code,
            nullif(trim(asp.payload_json ->> 'Informada'), '') as informada
        from latest_snapshot ls
        left join api_source_payload asp
            on asp.id = ls.payload_id
    )
    select
        sn.notice_id,
        sn.external_notice_code,
        coalesce(sn.notice_title, bi.normalized_title) as title,
        coalesce(sn.notice_description_raw, bi.normalized_description) as notice_description_raw,
        coalesce(sn.notice_status_name, bi.normalized_official_status) as official_status,
        coalesce(sn.mp_estado_codigo, ls.snapshot_mp_estado_codigo) as mp_estado_codigo,
        coalesce(
            sn.mp_estado_nombre,
            ls.snapshot_mp_estado_nombre,
            sn.notice_status_name,
            bi.normalized_official_status
        ) as mp_estado_nombre,
        coalesce(
            sn.mp_estado_canonical,
            lower(coalesce(ls.snapshot_mp_estado_nombre, sn.notice_status_name, bi.normalized_official_status))
        ) as mp_estado_canonical,
        sn.data_source_kind,
        sn.availability_context,
        coalesce(sn.procurement_method_code, ls.snapshot_codigo_tipo) as codigo_tipo,
        coalesce(sn.procurement_method_name, ls.snapshot_tipo, bi.normalized_tipo) as tipo,
        coalesce(ls.snapshot_tipo_convocatoria, bi.normalized_tipo_convocatoria) as tipo_convocatoria,
        lp.informada,
        coalesce(ls.snapshot_visibility_amount, bi.normalized_visibility_amount) as visibilidad_monto,
        ls.snapshot_funding_source as fuente_financiamiento,
        coalesce(sn.complaint_count, ls.snapshot_complaint_count) as complaint_count,
        coalesce(sn.estimated_amount, bi.normalized_estimated_amount) as estimated_amount,
        sn.currency_code,
        coalesce(sn.publication_date, bi.normalized_publication_date) as publication_date,
        coalesce(sn.close_date, bi.normalized_close_date) as close_date,
        coalesce(sn.award_date, bi.normalized_award_date) as award_date,
        coalesce(sn.estimated_award_date, bi.normalized_estimated_award_date) as estimated_award_date,
        sn.created_date,
        bi.buyer_name,
        coalesce(bi.buyer_region, ls.snapshot_buyer_region) as buyer_region,
        coalesce(bi.buyer_commune, ls.snapshot_buyer_commune) as buyer_commune,
        bi.contracting_unit_code,
        bi.contracting_unit_name,
        case
            when lower(coalesce(coalesce(sn.notice_status_name, bi.normalized_official_status), '')) like '%adjudicada%' then 'awarded'
            when lower(coalesce(coalesce(sn.notice_status_name, bi.normalized_official_status), '')) like '%revocada%'
              or lower(coalesce(coalesce(sn.notice_status_name, bi.normalized_official_status), '')) like '%suspendida%' then 'revoked_or_suspended'
            when coalesce(sn.close_date, bi.normalized_close_date) is null then 'unknown'
            when coalesce(sn.close_date, bi.normalized_close_date) < now() then 'closed'
            when coalesce(sn.close_date, bi.normalized_close_date) <= now() + interval '7 days' then 'closing_soon'
            else 'open'
        end as derived_stage
    from silver_notice sn
    left join buyer_info bi on bi.codigo_externo = sn.notice_id
    left join latest_snapshot ls on ls.external_notice_code = sn.notice_id
    left join latest_payload lp on lp.external_notice_code = sn.notice_id
    where sn.notice_id = :notice_id
    """
)

DETAIL_LINES_SQL = sa.text(
    """
    with bid_summary as (
        select
            notice_id,
            item_code,
            count(*) filter (where selected_offer_flag) as selected_offer_count
        from silver_bid_submission
        where notice_id = :notice_id
        group by notice_id, item_code
    ),
    notice_onu_ambiguity as (
        select
            notice_id,
            onu_product_code,
            count(*) as notice_onu_line_count
        from silver_notice_line
        where notice_id = :notice_id
          and onu_product_code is not null
        group by notice_id, onu_product_code
    ),
    po_line_summary as (
        select
            nl.notice_line_id,
            count(pol.purchase_order_line_id) as related_purchase_order_item_count
        from silver_notice_line nl
        left join silver_purchase_order_line pol
            on pol.linked_notice_id = nl.notice_id
           and pol.onu_product_code = nl.onu_product_code
        where nl.notice_id = :notice_id
        group by nl.notice_line_id
    )
    select
        nl.item_code,
        nl.line_number as correlative,
        nl.onu_product_code as product_code_onu,
        nl.line_name,
        nl.line_description_raw as line_description,
        nl.category_level_1 as category,
        nl.quantity_requested as quantity,
        nl.unit_of_measure as unit,
        nl.line_bid_count as offer_count,
        coalesce(bs.selected_offer_count, 0) as selected_offer_count,
        nl.line_supplier_count as supplier_count,
        coalesce(pol.related_purchase_order_item_count, 0) as related_purchase_order_item_count,
        case
            when coalesce(pol.related_purchase_order_item_count, 0) = 0 then 'none'
            when coalesce(pol.related_purchase_order_item_count, 0) = 1
             and coalesce(noa.notice_onu_line_count, 0) = 1 then 'medium'
            else 'low'
        end as relationship_certainty
    from silver_notice_line nl
    left join bid_summary bs
      on bs.notice_id = nl.notice_id
     and bs.item_code = nl.item_code
    left join po_line_summary pol
      on pol.notice_line_id = nl.notice_line_id
    left join notice_onu_ambiguity noa
      on noa.notice_id = nl.notice_id
     and noa.onu_product_code = nl.onu_product_code
    where nl.notice_id = :notice_id
    order by nl.line_number nulls last, nl.item_code
    """
)

DETAIL_OFFERS_SQL = sa.text(
    """
    select
        bs.supplier_key as supplier_code,
        coalesce(no.nombre_proveedor, ss.supplier_trade_name, ss.supplier_legal_name) as supplier_name,
        coalesce(no.nombre_oferta, bs.bid_submission_id::text) as offer_name,
        coalesce(no.codigo_item, bs.item_code) as item_code,
        coalesce(no.estado_oferta, bs.offer_status) as offer_status,
        coalesce(no.valor_total_ofertado, bs.total_price_offered) as offered_amount,
        coalesce(no.monto_unitario_oferta, bs.unit_price_offered) as unit_price,
        no.cantidad_ofertada as offered_quantity,
        coalesce(bs.offer_currency_name, 'CLP') as currency_code,
        coalesce(no.oferta_seleccionada, bs.selected_offer_flag) as is_selected,
        coalesce(no.fecha_envio_oferta, bs.offer_submission_date) as submitted_at
    from silver_bid_submission bs
    left join normalized_ofertas no
      on no.codigo_externo = bs.notice_id
     and no.supplier_key = bs.supplier_key
     and (
        no.codigo_item = bs.item_code
        or (no.codigo_item is null and bs.item_code is null)
     )
    left join silver_supplier ss
      on ss.supplier_id = bs.supplier_key
    where bs.notice_id = :notice_id
    order by coalesce(no.fecha_envio_oferta, bs.offer_submission_date) nulls last, bs.bid_submission_id
    """
)

DETAIL_PURCHASE_ORDERS_SQL = sa.text(
    """
    select
        po.purchase_order_id as purchase_order_code,
        po.purchase_order_status_name as purchase_order_status,
        po.order_created_at as purchase_order_created_at,
        po.total_amount as purchase_order_amount,
        po.currency_code
    from silver_purchase_order po
    where po.linked_notice_id = :notice_id
    order by po.order_created_at nulls last, po.purchase_order_id
    """
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    if len(parts) == 1:
        return name
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {_snake_to_camel(k): _jsonable(v) for k, v in row.items()}


def _relationship_summary(lines: list[dict[str, Any]]) -> str:
    certainties = {line.get("relationshipCertainty") for line in lines}
    if "low" in certainties:
        return "low"
    if "medium" in certainties:
        return "medium"
    if "none" in certainties:
        return "none"
    return "unconfirmed"


def _purchase_order_contract_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "purchaseOrderCode": row.get("purchaseOrderCode"),
        "purchaseOrderStatus": row.get("purchaseOrderStatus"),
        "purchaseOrderCreatedAt": row.get("purchaseOrderCreatedAt"),
        "purchaseOrderAmount": row.get("purchaseOrderAmount"),
        "currencyCode": row.get("currencyCode"),
        "purchaseOrderItemId": None,
        "purchaseOrderItemProductCodeOnu": None,
        "purchaseOrderItemNetTotal": None,
        "relationshipCertainty": "unconfirmed",
    }


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_informada(value: Any) -> bool:
    normalized = _normalized_text(value)
    return normalized in {"si", "sí", "true", "1", "informada"}


def _derive_availability(
    *,
    kind: str,
    has_data: bool,
    state_canonical: str | None,
    is_api_source: bool,
    data_source_kind: str | None,
    informada: bool,
) -> str:
    if has_data:
        return "available"

    if kind == "description":
        if not is_api_source:
            return "pipeline_missing"
        if _normalized_text(data_source_kind) != "api_detail":
            return "pending_detail"
        return "not_reported_by_source"

    if state_canonical == "publicada":
        if kind in {"participants", "offers"} and informada:
            return "not_reported_by_source"
        return "not_yet_public"

    if kind in {"award", "purchase_order"} and state_canonical in {"desierta", "revocada", "suspendida"}:
        return "not_applicable"

    if is_api_source:
        return "not_reported_by_source"
    return "pipeline_missing"


@router.get("", response_model=OpportunityListResponse)
def list_opportunities(
    page: int = Query(default=1, ge=1, le=OPPORTUNITY_PAGE_MAX),
    page_size: int = Query(
        default=OPPORTUNITY_PAGE_SIZE_DEFAULT, ge=1, le=OPPORTUNITY_PAGE_SIZE_MAX
    ),
    sort_by: str = Query(
        default="close_date", pattern=r"^(close_date|publication_date|estimated_amount|days_remaining)$"
    ),
    sort_order: str = Query(default="asc", pattern=r"^(asc|desc)$"),
    q: str | None = Query(default=None),
    official_status: str | None = Query(default=None),
    buyer_region: str | None = Query(default=None),
    primary_category: str | None = Query(default=None),
    publication_from: date | None = Query(default=None),
    publication_to: date | None = Query(default=None),
    close_from: date | None = Query(default=None),
    close_to: date | None = Query(default=None),
    min_amount: Decimal | None = Query(default=None, ge=0),
    max_amount: Decimal | None = Query(default=None, ge=0),
    procurement_type: str | None = Query(default=None, pattern=r"^(public|private|service)$"),
    less_than_100_utm: bool | None = Query(default=None),
    stage: str | None = Query(default=None),
    source_view: str | None = Query(default=None, pattern=r"^(publicadas)$"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    offset = (page - 1) * page_size
    shared_params = build_opportunities_filter_params(
        q=q,
        official_status=official_status,
        buyer_region=buyer_region,
        primary_category=primary_category,
        publication_from=publication_from,
        publication_to=publication_to,
        close_from=close_from,
        close_to=close_to,
        min_amount=min_amount,
        max_amount=max_amount,
        procurement_type=procurement_type,
        less_than_100_utm=less_than_100_utm,
        stage=stage,
        source_view=source_view,
    )

    total_row = db.execute(COUNT_SQL, shared_params).one()
    total = cast(int, total_row[0])

    rows = db.execute(
        LIST_SQL,
        {
            **shared_params,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page_size": page_size,
            "offset": offset,
        },
    ).mappings()

    items = [_row_to_dict(cast(dict[str, Any], row)) for row in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/summary", response_model=OpportunitySummaryResponse)
def get_opportunities_summary(
    page: int = Query(default=1, ge=1, le=OPPORTUNITY_PAGE_MAX),
    page_size: int = Query(
        default=OPPORTUNITY_PAGE_SIZE_DEFAULT, ge=1, le=OPPORTUNITY_PAGE_SIZE_MAX
    ),
    sort_by: str = Query(
        default="close_date", pattern=r"^(close_date|publication_date|estimated_amount|days_remaining)$"
    ),
    sort_order: str = Query(default="asc", pattern=r"^(asc|desc)$"),
    q: str | None = Query(default=None),
    official_status: str | None = Query(default=None),
    buyer_region: str | None = Query(default=None),
    primary_category: str | None = Query(default=None),
    publication_from: date | None = Query(default=None),
    publication_to: date | None = Query(default=None),
    close_from: date | None = Query(default=None),
    close_to: date | None = Query(default=None),
    min_amount: Decimal | None = Query(default=None, ge=0),
    max_amount: Decimal | None = Query(default=None, ge=0),
    procurement_type: str | None = Query(default=None, pattern=r"^(public|private|service)$"),
    less_than_100_utm: bool | None = Query(default=None),
    stage: str | None = Query(default=None),
    source_view: str | None = Query(default=None, pattern=r"^(publicadas)$"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = db.execute(
        SUMMARY_SQL,
        build_opportunities_filter_params(
            q=q,
            official_status=official_status,
            buyer_region=buyer_region,
            primary_category=primary_category,
            publication_from=publication_from,
            publication_to=publication_to,
            close_from=close_from,
            close_to=close_to,
            min_amount=min_amount,
            max_amount=max_amount,
            procurement_type=procurement_type,
            less_than_100_utm=less_than_100_utm,
            stage=stage,
            source_view=source_view,
        ),
    ).one()

    metrics = [
        {"key": "total_opportunities", "label": "Total oportunidades", "value": _jsonable(row[0])},
        {"key": "open", "label": "Abiertas", "value": _jsonable(row[2])},
        {"key": "closing_soon", "label": "Cierran pronto", "value": _jsonable(row[3])},
        {"key": "closed", "label": "Cerradas", "value": _jsonable(row[4])},
        {"key": "awarded", "label": "Adjudicadas", "value": _jsonable(row[5])},
        {
            "key": "revoked_or_suspended",
            "label": "Revocadas o suspendidas",
            "value": _jsonable(row[6]),
        },
        {
            "key": "mp_publicada",
            "label": "Estado Publicada",
            "value": _jsonable(row[7]),
        },
        {
            "key": "source_publicadas",
            "label": "Fuente API Publicadas/Detail",
            "value": _jsonable(row[8]),
        },
        {
            "key": "availability_publicadas",
            "label": "Contexto Publicadas",
            "value": _jsonable(row[9]),
        },
        {"key": "unknown_stage", "label": "Sin clasificar", "value": _jsonable(row[1])},
        {
            "key": "avg_estimated_amount",
            "label": "Monto promedio estimado",
            "value": _jsonable(row[11]),
        },
        {
            "key": "total_estimated_amount",
            "label": "Monto total estimado",
            "value": _jsonable(row[12]),
        },
    ]

    return {"metrics": metrics}


@router.get("/{notice_id}", response_model=OpportunityDetailResponse)
def get_opportunity_detail(
    notice_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    detail_row = db.execute(DETAIL_SQL, {"notice_id": notice_id}).mappings().first()
    if not detail_row:
        raise HTTPException(status_code=404, detail="opportunity not found")

    detail = _row_to_dict(cast(dict[str, Any], detail_row))

    lines_rows = db.execute(DETAIL_LINES_SQL, {"notice_id": notice_id}).mappings()
    lines = [_row_to_dict(cast(dict[str, Any], row)) for row in lines_rows]

    offers_rows = db.execute(DETAIL_OFFERS_SQL, {"notice_id": notice_id}).mappings()
    offers = [_row_to_dict(cast(dict[str, Any], row)) for row in offers_rows]

    po_rows = db.execute(DETAIL_PURCHASE_ORDERS_SQL, {"notice_id": notice_id}).mappings()
    purchase_orders = [
        _purchase_order_contract_row(_row_to_dict(cast(dict[str, Any], row)))
        for row in po_rows
    ]

    timeline = [
        {
            "key": "publication",
            "label": "Publicación",
            "date": detail.get("publicationDate"),
            "source": "official",
        },
        {"key": "close", "label": "Cierre", "date": detail.get("closeDate"), "source": "official"},
        {
            "key": "estimated_award",
            "label": "Adjudicación estimada",
            "date": detail.get("estimatedAwardDate"),
            "source": "official",
        },
        {"key": "award", "label": "Adjudicación", "date": detail.get("awardDate"), "source": "official"},
    ]

    state_canonical_raw = detail.get("mpEstadoCanonical")
    state_canonical = _normalized_text(state_canonical_raw) or None
    is_api_source = _normalized_text(detail.get("dataSourceKind")).startswith("api_")
    informada = _is_informada(detail.get("informada"))
    has_participants_data = any((line.get("supplierCount") or 0) > 0 for line in lines)
    has_offers_data = len(offers) > 0
    has_award_data = detail.get("awardDate") is not None
    has_purchase_order_data = len(purchase_orders) > 0
    has_description_data = _normalized_text(detail.get("noticeDescriptionRaw")) != ""

    participants_availability = _derive_availability(
        kind="participants",
        has_data=has_participants_data,
        state_canonical=state_canonical,
        is_api_source=is_api_source,
        data_source_kind=detail.get("dataSourceKind"),
        informada=informada,
    )
    offers_availability = _derive_availability(
        kind="offers",
        has_data=has_offers_data,
        state_canonical=state_canonical,
        is_api_source=is_api_source,
        data_source_kind=detail.get("dataSourceKind"),
        informada=informada,
    )
    award_availability = _derive_availability(
        kind="award",
        has_data=has_award_data,
        state_canonical=state_canonical,
        is_api_source=is_api_source,
        data_source_kind=detail.get("dataSourceKind"),
        informada=informada,
    )
    purchase_order_availability = _derive_availability(
        kind="purchase_order",
        has_data=has_purchase_order_data,
        state_canonical=state_canonical,
        is_api_source=is_api_source,
        data_source_kind=detail.get("dataSourceKind"),
        informada=informada,
    )
    description_availability = _derive_availability(
        kind="description",
        has_data=has_description_data,
        state_canonical=state_canonical,
        is_api_source=is_api_source,
        data_source_kind=detail.get("dataSourceKind"),
        informada=informada,
    )

    return {
        "noticeId": detail["noticeId"],
        "externalNoticeCode": detail.get("externalNoticeCode"),
        "title": detail.get("title"),
        "officialStatus": detail.get("officialStatus"),
        "mpEstadoCodigo": detail.get("mpEstadoCodigo"),
        "mpEstadoNombre": detail.get("mpEstadoNombre"),
        "mpEstadoCanonical": detail.get("mpEstadoCanonical"),
        "dataSourceKind": detail.get("dataSourceKind"),
        "availabilityContext": detail.get("availabilityContext"),
        "codigoTipo": detail.get("codigoTipo"),
        "tipo": detail.get("tipo"),
        "tipoConvocatoria": detail.get("tipoConvocatoria"),
        "informada": detail.get("informada"),
        "visibilidadMonto": detail.get("visibilidadMonto"),
        "fuenteFinanciamiento": detail.get("fuenteFinanciamiento"),
        "complaintCount": detail.get("complaintCount"),
        "noticeDescriptionRaw": detail.get("noticeDescriptionRaw"),
        "derivedStage": detail.get("derivedStage"),
        "estimatedAmount": detail.get("estimatedAmount"),
        "currencyCode": detail.get("currencyCode"),
        "participantsAvailability": participants_availability,
        "offersAvailability": offers_availability,
        "awardAvailability": award_availability,
        "purchaseOrderAvailability": purchase_order_availability,
        "descriptionAvailability": description_availability,
        "buyer": {
            "buyerName": detail.get("buyerName"),
            "buyerRegion": detail.get("buyerRegion"),
            "buyerCommune": detail.get("buyerCommune"),
            "contractingUnitName": detail.get("contractingUnitName"),
            "contractingUnitCode": detail.get("contractingUnitCode"),
        },
        "relationshipSummary": _relationship_summary(lines),
        "timeline": timeline,
        "lines": lines,
        "offers": offers,
        "purchaseOrders": purchase_orders,
    }
