from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


def _contains_filter(value: str | None) -> str | None:
    return f"%{value}%" if value else None


def build_opportunities_filter_params(
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


def _shared_filter_sql(
    *,
    q_clause: str,
    buyer_region_clause: str,
    primary_category_clause: str,
    less_than_100_utm_clause: str,
    procurement_public_expr: str,
    procurement_private_expr: str,
    procurement_service_expr: str,
) -> str:
    return f"""
    where (cast(:q as text) is null or (
            {q_clause}
        ))
      and (cast(:official_status as text) is null or sn.notice_status_name ilike :official_status)
      and (cast(:buyer_region as text) is null or {buyer_region_clause})
      and (cast(:primary_category as text) is null or {primary_category_clause})
      and (cast(:publication_from as timestamp) is null or sn.publication_date >= :publication_from)
      and (cast(:publication_to as timestamp) is null or sn.publication_date < :publication_to + interval '1 day')
      and (cast(:close_from as timestamp) is null or sn.close_date >= :close_from)
      and (cast(:close_to as timestamp) is null or sn.close_date < :close_to + interval '1 day')
      and (cast(:min_amount as numeric) is null or sn.estimated_amount >= :min_amount)
      and (cast(:max_amount as numeric) is null or sn.estimated_amount <= :max_amount)
      and (cast(:less_than_100_utm as boolean) is null or {less_than_100_utm_clause})
      and (cast(:procurement_type as text) is null or
           case
               when :procurement_type = 'public' then {procurement_public_expr}
               when :procurement_type = 'private' then {procurement_private_expr}
               when :procurement_type = 'service' then {procurement_service_expr}
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


LIST_FILTER_SQL = _shared_filter_sql(
    q_clause="""
sn.notice_title ilike :q
            or sn.external_notice_code ilike :q
            or bi.buyer_name ilike :q
            or bi.primary_category ilike :q
""",
    buyer_region_clause="bi.buyer_region ilike :buyer_region",
    primary_category_clause="bi.primary_category ilike :primary_category",
    less_than_100_utm_clause="bi.flag_menos_100_utm = :less_than_100_utm",
    procurement_public_expr="coalesce(sn.is_public_tender_flag, bi.flag_licitacion_publica)",
    procurement_private_expr="coalesce(sn.is_private_tender_flag, bi.flag_licitacion_privada)",
    procurement_service_expr="coalesce(bi.flag_licitacion_servicios, false)",
)

COUNT_AND_SUMMARY_FILTER_SQL = _shared_filter_sql(
    q_clause="""
sn.notice_title ilike :q
            or sn.external_notice_code ilike :q
            or nl.nombre_unidad ilike :q
""",
    buyer_region_clause="nl.region_unidad ilike :buyer_region",
    primary_category_clause="""
exists (
            select 1 from normalized_licitacion_items nli
            where nli.codigo_externo = nl.codigo_externo
              and coalesce(nli.rubro1, nli.rubro2, nli.rubro3) ilike :primary_category
        )
""",
    less_than_100_utm_clause="nl.flag_menos_100_utm = :less_than_100_utm",
    procurement_public_expr="coalesce(sn.is_public_tender_flag, nl.flag_licitacion_publica)",
    procurement_private_expr="coalesce(sn.is_private_tender_flag, nl.flag_licitacion_privada)",
    procurement_service_expr="coalesce(nl.flag_licitacion_servicios, false)",
)
