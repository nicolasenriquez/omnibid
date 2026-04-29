from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

OPPORTUNITY_PAGE_SIZE_DEFAULT = 20
OPPORTUNITY_PAGE_SIZE_MAX = 100
OPPORTUNITY_PAGE_MAX = 500

LIST_SQL = sa.text(
    """
    with buyer_info as (
        select distinct on (nl.codigo_externo)
            nl.codigo_externo,
            nl.nombre_unidad as buyer_name,
            nl.region_unidad as buyer_region,
            nl.tipo_adquisicion_norm as procurement_method,
            nl.flag_licitacion_publica,
            nl.flag_licitacion_privada,
            nl.flag_licitacion_servicios,
            nl.flag_menos_100_utm,
            coalesce(nullif(nli.rubro1, ''), nullif(nli.rubro2, ''), nullif(nli.rubro3, '')) as primary_category
        from normalized_licitaciones nl
        left join normalized_licitacion_items nli
            on nli.codigo_externo = nl.codigo_externo
    )
    select
        sn.notice_id,
        sn.external_notice_code,
        sn.notice_title as title,
        sn.notice_status_name as official_status,
        sn.estimated_amount,
        sn.currency_code,
        sn.publication_date,
        sn.close_date,
        sn.notice_line_count as line_count,
        sn.notice_bid_count as bid_count,
        sn.notice_supplier_count as supplier_count,
        sn.notice_purchase_order_count as purchase_order_count,
        bi.buyer_name,
        bi.buyer_region,
        bi.primary_category,
        case
            when coalesce(sn.is_public_tender_flag, bi.flag_licitacion_publica) then 'public'
            when coalesce(sn.is_private_tender_flag, bi.flag_licitacion_privada) then 'private'
            when coalesce(bi.flag_licitacion_servicios, false) then 'service'
            else null
        end as procurement_type,
        coalesce(bi.flag_menos_100_utm, false) as is_less_than_100_utm,
        case
            when sn.close_date is null then null
            else greatest(0, floor(extract(epoch from (sn.close_date - now())) / 86400))::int
        end as days_remaining,
        case
            when lower(coalesce(sn.notice_status_name, '')) like '%adjudicada%' then 'awarded'
            when lower(coalesce(sn.notice_status_name, '')) like '%revocada%'
              or lower(coalesce(sn.notice_status_name, '')) like '%suspendida%' then 'revoked_or_suspended'
            when sn.close_date is null then 'unknown'
            when sn.close_date < now() then 'closed'
            when sn.close_date <= now() + interval '7 days' then 'closing_soon'
            else 'open'
        end as derived_stage
    from silver_notice sn
    left join buyer_info bi on bi.codigo_externo = sn.notice_id
    where (cast(:q as text) is null or (
            sn.notice_title ilike :q
            or sn.external_notice_code ilike :q
            or bi.buyer_name ilike :q
            or bi.primary_category ilike :q
        ))
      and (cast(:official_status as text) is null or sn.notice_status_name ilike :official_status)
      and (cast(:buyer_region as text) is null or bi.buyer_region ilike :buyer_region)
      and (cast(:primary_category as text) is null or bi.primary_category ilike :primary_category)
      and (cast(:publication_from as timestamp) is null or sn.publication_date >= :publication_from)
      and (cast(:publication_to as timestamp) is null or sn.publication_date < :publication_to + interval '1 day')
      and (cast(:close_from as timestamp) is null or sn.close_date >= :close_from)
      and (cast(:close_to as timestamp) is null or sn.close_date < :close_to + interval '1 day')
      and (cast(:min_amount as numeric) is null or sn.estimated_amount >= :min_amount)
      and (cast(:max_amount as numeric) is null or sn.estimated_amount <= :max_amount)
      and (cast(:less_than_100_utm as boolean) is null or bi.flag_menos_100_utm = :less_than_100_utm)
      and (cast(:procurement_type as text) is null or
           case
               when :procurement_type = 'public' then coalesce(sn.is_public_tender_flag, bi.flag_licitacion_publica)
               when :procurement_type = 'private' then coalesce(sn.is_private_tender_flag, bi.flag_licitacion_privada)
               when :procurement_type = 'service' then coalesce(bi.flag_licitacion_servicios, false)
               else true
           end)
      and (cast(:stage as text) is null or
           case
               when :stage = 'open' then sn.close_date > now() + interval '7 days'
               when :stage = 'closing_soon' then sn.close_date > now() and sn.close_date <= now() + interval '7 days'
               when :stage = 'closed' then sn.close_date <= now()
                 and lower(coalesce(sn.notice_status_name, '')) not like '%adjudicada%'
                 and lower(coalesce(sn.notice_status_name, '')) not like '%revocada%'
                 and lower(coalesce(sn.notice_status_name, '')) not like '%suspendida%'
               when :stage = 'awarded' then lower(coalesce(sn.notice_status_name, '')) like '%adjudicada%'
               when :stage = 'revoked_or_suspended' then lower(coalesce(sn.notice_status_name, '')) like '%revocada%'
                 or lower(coalesce(sn.notice_status_name, '')) like '%suspendida%'
               when :stage = 'unknown' then sn.close_date is null
               else true
           end)
    order by
        case when :sort_by = 'close_date' and :sort_order = 'asc' then sn.close_date end asc nulls last,
        case when :sort_by = 'close_date' and :sort_order = 'desc' then sn.close_date end desc nulls last,
        case when :sort_by = 'publication_date' and :sort_order = 'asc' then sn.publication_date end asc nulls last,
        case when :sort_by = 'publication_date' and :sort_order = 'desc' then sn.publication_date end desc nulls last,
        case when :sort_by = 'estimated_amount' and :sort_order = 'asc' then sn.estimated_amount end asc nulls last,
        case when :sort_by = 'estimated_amount' and :sort_order = 'desc' then sn.estimated_amount end desc nulls last,
        case when :sort_by = 'days_remaining' and :sort_order = 'asc' then sn.close_date end asc nulls last,
        case when :sort_by = 'days_remaining' and :sort_order = 'desc' then sn.close_date end desc nulls last
    limit :page_size
    offset :offset
    """
)

COUNT_SQL = sa.text(
    """
    select count(*) as total
    from silver_notice sn
    left join normalized_licitaciones nl on nl.codigo_externo = sn.notice_id
    where (cast(:q as text) is null or (
            sn.notice_title ilike :q
            or sn.external_notice_code ilike :q
            or nl.nombre_unidad ilike :q
        ))
      and (cast(:official_status as text) is null or sn.notice_status_name ilike :official_status)
      and (cast(:buyer_region as text) is null or nl.region_unidad ilike :buyer_region)
      and (cast(:primary_category as text) is null or exists (
            select 1 from normalized_licitacion_items nli
            where nli.codigo_externo = nl.codigo_externo
              and coalesce(nli.rubro1, nli.rubro2, nli.rubro3) ilike :primary_category
        ))
      and (cast(:publication_from as timestamp) is null or sn.publication_date >= :publication_from)
      and (cast(:publication_to as timestamp) is null or sn.publication_date < :publication_to + interval '1 day')
      and (cast(:close_from as timestamp) is null or sn.close_date >= :close_from)
      and (cast(:close_to as timestamp) is null or sn.close_date < :close_to + interval '1 day')
      and (cast(:min_amount as numeric) is null or sn.estimated_amount >= :min_amount)
      and (cast(:max_amount as numeric) is null or sn.estimated_amount <= :max_amount)
      and (cast(:less_than_100_utm as boolean) is null or nl.flag_menos_100_utm = :less_than_100_utm)
      and (cast(:procurement_type as text) is null or
           case
               when :procurement_type = 'public' then coalesce(sn.is_public_tender_flag, nl.flag_licitacion_publica)
               when :procurement_type = 'private' then coalesce(sn.is_private_tender_flag, nl.flag_licitacion_privada)
               when :procurement_type = 'service' then coalesce(nl.flag_licitacion_servicios, false)
               else true
           end)
      and (cast(:stage as text) is null or
           case
               when :stage = 'open' then sn.close_date > now() + interval '7 days'
               when :stage = 'closing_soon' then sn.close_date > now() and sn.close_date <= now() + interval '7 days'
               when :stage = 'closed' then sn.close_date <= now()
                 and lower(coalesce(sn.notice_status_name, '')) not like '%adjudicada%'
                 and lower(coalesce(sn.notice_status_name, '')) not like '%revocada%'
                 and lower(coalesce(sn.notice_status_name, '')) not like '%suspendida%'
               when :stage = 'awarded' then lower(coalesce(sn.notice_status_name, '')) like '%adjudicada%'
               when :stage = 'revoked_or_suspended' then lower(coalesce(sn.notice_status_name, '')) like '%revocada%'
                 or lower(coalesce(sn.notice_status_name, '')) like '%suspendida%'
               when :stage = 'unknown' then sn.close_date is null
               else true
           end)
    """
)

SUMMARY_SQL = sa.text(
    """
    select
        count(*) as total_opportunities,
        count(*) filter (where close_date is null) as unknown_stage,
        count(*) filter (where close_date > now() + interval '7 days') as open,
        count(*) filter (where close_date > now() and close_date <= now() + interval '7 days') as closing_soon,
        count(*) filter (
            where close_date <= now()
              and lower(coalesce(notice_status_name, '')) not like '%adjudicada%'
              and lower(coalesce(notice_status_name, '')) not like '%revocada%'
              and lower(coalesce(notice_status_name, '')) not like '%suspendida%'
        ) as closed,
        count(*) filter (where lower(coalesce(notice_status_name, '')) like '%adjudicada%') as awarded,
        count(*) filter (
            where lower(coalesce(notice_status_name, '')) like '%revocada%'
               or lower(coalesce(notice_status_name, '')) like '%suspendida%'
        ) as revoked_or_suspended,
        count(*) filter (where estimated_amount is not null) as with_estimated_amount,
        coalesce(avg(estimated_amount) filter (where estimated_amount is not null), 0) as avg_estimated_amount,
        coalesce(sum(estimated_amount) filter (where estimated_amount is not null), 0) as total_estimated_amount
    from silver_notice sn
    left join normalized_licitaciones nl on nl.codigo_externo = sn.notice_id
    where (cast(:q as text) is null or (
            sn.notice_title ilike :q
            or sn.external_notice_code ilike :q
            or nl.nombre_unidad ilike :q
        ))
      and (cast(:official_status as text) is null or sn.notice_status_name ilike :official_status)
      and (cast(:buyer_region as text) is null or nl.region_unidad ilike :buyer_region)
      and (cast(:primary_category as text) is null or exists (
            select 1 from normalized_licitacion_items nli
            where nli.codigo_externo = nl.codigo_externo
              and coalesce(nli.rubro1, nli.rubro2, nli.rubro3) ilike :primary_category
        ))
      and (cast(:publication_from as timestamp) is null or sn.publication_date >= :publication_from)
      and (cast(:publication_to as timestamp) is null or sn.publication_date < :publication_to + interval '1 day')
      and (cast(:close_from as timestamp) is null or sn.close_date >= :close_from)
      and (cast(:close_to as timestamp) is null or sn.close_date < :close_to + interval '1 day')
      and (cast(:min_amount as numeric) is null or sn.estimated_amount >= :min_amount)
      and (cast(:max_amount as numeric) is null or sn.estimated_amount <= :max_amount)
      and (cast(:less_than_100_utm as boolean) is null or nl.flag_menos_100_utm = :less_than_100_utm)
      and (cast(:procurement_type as text) is null or
           case
               when :procurement_type = 'public' then coalesce(sn.is_public_tender_flag, nl.flag_licitacion_publica)
               when :procurement_type = 'private' then coalesce(sn.is_private_tender_flag, nl.flag_licitacion_privada)
               when :procurement_type = 'service' then coalesce(nl.flag_licitacion_servicios, false)
               else true
           end)
      and (cast(:stage as text) is null or
           case
               when :stage = 'open' then sn.close_date > now() + interval '7 days'
               when :stage = 'closing_soon' then sn.close_date > now() and sn.close_date <= now() + interval '7 days'
               when :stage = 'closed' then sn.close_date <= now()
                 and lower(coalesce(sn.notice_status_name, '')) not like '%adjudicada%'
                 and lower(coalesce(sn.notice_status_name, '')) not like '%revocada%'
                 and lower(coalesce(sn.notice_status_name, '')) not like '%suspendida%'
               when :stage = 'awarded' then lower(coalesce(sn.notice_status_name, '')) like '%adjudicada%'
               when :stage = 'revoked_or_suspended' then lower(coalesce(sn.notice_status_name, '')) like '%revocada%'
                 or lower(coalesce(sn.notice_status_name, '')) like '%suspendida%'
               when :stage = 'unknown' then sn.close_date is null
               else true
           end)
    """
)

DETAIL_SQL = sa.text(
    """
    with buyer_info as (
        select
            nl.codigo_externo,
            nl.nombre_unidad as buyer_name,
            nl.region_unidad as buyer_region,
            nl.codigo_unidad as contracting_unit_code,
            nl.nombre_unidad as contracting_unit_name
        from normalized_licitaciones nl
    )
    select
        sn.notice_id,
        sn.external_notice_code,
        sn.notice_title as title,
        sn.notice_status_name as official_status,
        sn.estimated_amount,
        sn.currency_code,
        sn.publication_date,
        sn.close_date,
        sn.award_date,
        sn.estimated_award_date,
        sn.created_date,
        bi.buyer_name,
        bi.buyer_region,
        bi.contracting_unit_code,
        bi.contracting_unit_name,
        case
            when lower(coalesce(sn.notice_status_name, '')) like '%adjudicada%' then 'awarded'
            when lower(coalesce(sn.notice_status_name, '')) like '%revocada%'
              or lower(coalesce(sn.notice_status_name, '')) like '%suspendida%' then 'revoked_or_suspended'
            when sn.close_date is null then 'unknown'
            when sn.close_date < now() then 'closed'
            when sn.close_date <= now() + interval '7 days' then 'closing_soon'
            else 'open'
        end as derived_stage
    from silver_notice sn
    left join buyer_info bi on bi.codigo_externo = sn.notice_id
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
        bs.offer_status,
        bs.total_price_offered as offered_amount,
        bs.offer_currency_name as currency_code,
        bs.selected_offer_flag as is_selected,
        bs.offer_submission_date as submitted_at
    from silver_bid_submission bs
    where bs.notice_id = :notice_id
    order by bs.offer_submission_date nulls last, bs.bid_submission_id
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


def _contains_filter(value: str | None) -> str | None:
    return f"%{value}%" if value else None


def _shared_filter_params(
    *,
    q: str | None,
    official_status: str | None,
    buyer_region: str | None,
    primary_category: str | None,
    publication_from: date | None,
    publication_to: date | None,
    close_from: date | None,
    close_to: date | None,
    min_amount: Decimal | None,
    max_amount: Decimal | None,
    procurement_type: str | None,
    less_than_100_utm: bool | None,
    stage: str | None,
) -> dict[str, Any]:
    return {
        "q": _contains_filter(q),
        "official_status": _contains_filter(official_status),
        "buyer_region": _contains_filter(buyer_region),
        "primary_category": _contains_filter(primary_category),
        "publication_from": publication_from,
        "publication_to": publication_to,
        "close_from": close_from,
        "close_to": close_to,
        "min_amount": min_amount,
        "max_amount": max_amount,
        "procurement_type": procurement_type,
        "less_than_100_utm": less_than_100_utm,
        "stage": stage,
    }


@router.get("")
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
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    offset = (page - 1) * page_size
    shared_params = _shared_filter_params(
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


@router.get("/summary")
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
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = db.execute(
        SUMMARY_SQL,
        _shared_filter_params(
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
        {"key": "unknown_stage", "label": "Sin clasificar", "value": _jsonable(row[1])},
        {
            "key": "avg_estimated_amount",
            "label": "Monto promedio estimado",
            "value": _jsonable(row[8]),
        },
        {
            "key": "total_estimated_amount",
            "label": "Monto total estimado",
            "value": _jsonable(row[9]),
        },
    ]

    return {"metrics": metrics}


@router.get("/{notice_id}")
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
    purchase_orders = [_row_to_dict(cast(dict[str, Any], row)) for row in po_rows]

    timeline = [
        {
            "key": "publication",
            "label": "Publicacion",
            "date": detail.get("publication_date"),
            "source": "official",
        },
        {"key": "close", "label": "Cierre", "date": detail.get("close_date"), "source": "official"},
        {
            "key": "estimated_award",
            "label": "Adjudicacion estimada",
            "date": detail.get("estimated_award_date"),
            "source": "official",
        },
        {"key": "award", "label": "Adjudicacion", "date": detail.get("award_date"), "source": "official"},
    ]

    return {
        "noticeId": detail["noticeId"],
        "externalNoticeCode": detail.get("externalNoticeCode"),
        "title": detail.get("title"),
        "officialStatus": detail.get("officialStatus"),
        "derivedStage": detail.get("derivedStage"),
        "estimatedAmount": detail.get("estimatedAmount"),
        "currencyCode": detail.get("currencyCode"),
        "buyer": {
            "buyerName": detail.get("buyerName"),
            "buyerRegion": detail.get("buyerRegion"),
            "contractingUnitName": detail.get("contractingUnitName"),
            "contractingUnitCode": detail.get("contractingUnitCode"),
        },
        "relationshipSummary": _relationship_summary(lines),
        "timeline": timeline,
        "lines": lines,
        "offers": offers,
        "purchaseOrders": purchase_orders,
    }
