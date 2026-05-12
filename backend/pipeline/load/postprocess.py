from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.models.normalized import (
    SilverAwardOutcome,
    SilverBidSubmission,
    SilverNotice,
    SilverNoticeLine,
    SilverNoticePurchaseOrderLink,
    SilverPurchaseOrder,
    SilverPurchaseOrderLine,
)

SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS = ["notice_id", "purchase_order_id", "link_type"]


def refresh_silver_notice_and_line_enrichments(session: Session) -> None:
    notice_line_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverNoticeLine)
        .where(SilverNoticeLine.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )
    notice_bid_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverBidSubmission)
        .where(SilverBidSubmission.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )
    notice_supplier_count_sq = (
        sa.select(sa.func.count(sa.distinct(SilverBidSubmission.supplier_key)))
        .select_from(SilverBidSubmission)
        .where(SilverBidSubmission.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )
    notice_selected_bid_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverBidSubmission)
        .where(
            SilverBidSubmission.notice_id == SilverNotice.notice_id,
            SilverBidSubmission.selected_offer_flag.is_(True),
        )
        .scalar_subquery()
    )
    notice_awarded_line_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverAwardOutcome)
        .where(
            SilverAwardOutcome.notice_id == SilverNotice.notice_id,
            sa.or_(
                SilverAwardOutcome.selected_offer_flag.is_(True),
                SilverAwardOutcome.awarded_line_amount.is_not(None),
            ),
        )
        .scalar_subquery()
    )
    notice_purchase_order_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverNoticePurchaseOrderLink)
        .where(SilverNoticePurchaseOrderLink.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )

    session.execute(
        sa.update(SilverNotice).values(
            notice_line_count=sa.func.coalesce(notice_line_count_sq, 0),
            notice_bid_count=sa.func.coalesce(notice_bid_count_sq, 0),
            notice_supplier_count=sa.func.coalesce(notice_supplier_count_sq, 0),
            notice_selected_bid_count=sa.func.coalesce(notice_selected_bid_count_sq, 0),
            notice_awarded_line_count=sa.func.coalesce(notice_awarded_line_count_sq, 0),
            notice_purchase_order_count=sa.func.coalesce(notice_purchase_order_count_sq, 0),
            notice_has_purchase_order_flag=sa.case(
                (sa.func.coalesce(notice_purchase_order_count_sq, 0) > 0, True),
                else_=False,
            ),
            notice_awarded_to_order_conversion_flag=sa.case(
                (
                    sa.and_(
                        sa.func.coalesce(notice_awarded_line_count_sq, 0) > 0,
                        sa.func.coalesce(notice_purchase_order_count_sq, 0) > 0,
                    ),
                    True,
                ),
                else_=False,
            ),
            updated_at=sa.func.now(),
        )
    )

    line_bid_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverBidSubmission)
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_supplier_count_sq = (
        sa.select(sa.func.count(sa.distinct(SilverBidSubmission.supplier_key)))
        .select_from(SilverBidSubmission)
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_min_offer_amount_sq = (
        sa.select(sa.func.min(SilverBidSubmission.total_price_offered))
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_max_offer_amount_sq = (
        sa.select(sa.func.max(SilverBidSubmission.total_price_offered))
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_avg_offer_amount_sq = (
        sa.select(sa.func.avg(SilverBidSubmission.total_price_offered))
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_median_offer_amount_sq = (
        sa.select(
            sa.func.percentile_cont(0.5).within_group(SilverBidSubmission.total_price_offered)
        )
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )

    session.execute(
        sa.update(SilverNoticeLine).values(
            line_bid_count=sa.func.coalesce(line_bid_count_sq, 0),
            line_supplier_count=sa.func.coalesce(line_supplier_count_sq, 0),
            line_min_offer_amount=line_min_offer_amount_sq,
            line_max_offer_amount=line_max_offer_amount_sq,
            line_avg_offer_amount=line_avg_offer_amount_sq,
            line_median_offer_amount=line_median_offer_amount_sq,
            line_price_dispersion_ratio=sa.case(
                (
                    sa.and_(
                        line_avg_offer_amount_sq.is_not(None),
                        line_avg_offer_amount_sq != 0,
                        line_min_offer_amount_sq.is_not(None),
                        line_max_offer_amount_sq.is_not(None),
                    ),
                    (line_max_offer_amount_sq - line_min_offer_amount_sq) / line_avg_offer_amount_sq,
                ),
                else_=None,
            ),
            updated_at=sa.func.now(),
        )
    )


def refresh_silver_purchase_order_enrichments(session: Session) -> None:
    line_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverPurchaseOrderLine)
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )
    total_quantity_sq = (
        sa.select(sa.func.sum(SilverPurchaseOrderLine.quantity_ordered))
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )
    total_net_amount_sq = (
        sa.select(sa.func.sum(SilverPurchaseOrderLine.line_net_total))
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )
    unique_product_count_sq = (
        sa.select(sa.func.count(sa.distinct(SilverPurchaseOrderLine.onu_product_code)))
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )

    session.execute(
        sa.update(SilverPurchaseOrder).values(
            purchase_order_line_count=sa.func.coalesce(line_count_sq, 0),
            purchase_order_total_quantity=total_quantity_sq,
            purchase_order_total_net_amount=total_net_amount_sq,
            purchase_order_unique_product_count=sa.func.coalesce(unique_product_count_sq, 0),
            is_linked_to_notice_flag=sa.case(
                (SilverPurchaseOrder.linked_notice_id.is_not(None), True),
                else_=False,
            ),
            updated_at=sa.func.now(),
        )
    )


def reconcile_silver_notice_purchase_order_links(session: Session) -> int:
    link_type = "explicit_code_match"
    insert_stmt = pg_insert(SilverNoticePurchaseOrderLink).from_select(
        [
            "notice_id",
            "purchase_order_id",
            "link_type",
            "link_confidence",
            "source_system",
            "source_file_id",
        ],
        sa.select(
            SilverPurchaseOrder.linked_notice_id.label("notice_id"),
            SilverPurchaseOrder.purchase_order_id.label("purchase_order_id"),
            sa.literal(link_type).label("link_type"),
            sa.literal(1).label("link_confidence"),
            sa.literal("mercado_publico_csv").label("source_system"),
            SilverPurchaseOrder.source_file_id.label("source_file_id"),
        )
        .join(
            SilverNotice,
            SilverNotice.notice_id == SilverPurchaseOrder.linked_notice_id,
        )
        .outerjoin(
            SilverNoticePurchaseOrderLink,
            sa.and_(
                SilverNoticePurchaseOrderLink.notice_id == SilverPurchaseOrder.linked_notice_id,
                SilverNoticePurchaseOrderLink.purchase_order_id
                == SilverPurchaseOrder.purchase_order_id,
                SilverNoticePurchaseOrderLink.link_type == link_type,
            ),
        )
        .where(
            SilverPurchaseOrder.linked_notice_id.is_not(None),
            SilverNoticePurchaseOrderLink.notice_purchase_order_link_id.is_(None),
        ),
    )
    insert_stmt = insert_stmt.on_conflict_do_nothing(
        index_elements=SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS
    )
    result = cast(Any, session.execute(insert_stmt))
    return max(0, int(result.rowcount or 0))
