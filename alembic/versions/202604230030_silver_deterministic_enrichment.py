"""silver deterministic enrichment columns

Revision ID: 202604230030_silver_enrichment
Revises: 202604230020_silver_master
Create Date: 2026-04-23 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "202604230030_silver_enrichment"
down_revision: Union[str, None] = "202604230020_silver_master"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("silver_notice", sa.Column("days_publication_to_close", sa.Integer(), nullable=True))
    op.add_column("silver_notice", sa.Column("days_creation_to_close", sa.Integer(), nullable=True))
    op.add_column("silver_notice", sa.Column("days_close_to_award", sa.Integer(), nullable=True))
    op.add_column(
        "silver_notice",
        sa.Column(
            "has_missing_date_chain_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "silver_notice",
        sa.Column("is_public_tender_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "silver_notice",
        sa.Column("is_private_tender_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "silver_notice",
        sa.Column(
            "requires_toma_razon_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "silver_notice",
        sa.Column("multiple_stages_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "silver_notice",
        sa.Column("hidden_budget_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "silver_notice",
        sa.Column("has_extension_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "silver_notice",
        sa.Column("has_site_visit_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "silver_notice",
        sa.Column(
            "has_physical_document_delivery_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column("silver_notice", sa.Column("notice_line_count", sa.Integer(), nullable=True))
    op.add_column("silver_notice", sa.Column("notice_bid_count", sa.Integer(), nullable=True))
    op.add_column("silver_notice", sa.Column("notice_supplier_count", sa.Integer(), nullable=True))
    op.add_column("silver_notice", sa.Column("notice_selected_bid_count", sa.Integer(), nullable=True))
    op.add_column("silver_notice", sa.Column("notice_awarded_line_count", sa.Integer(), nullable=True))
    op.add_column(
        "silver_notice",
        sa.Column(
            "notice_has_purchase_order_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column("silver_notice", sa.Column("notice_purchase_order_count", sa.Integer(), nullable=True))
    op.add_column(
        "silver_notice",
        sa.Column(
            "notice_awarded_to_order_conversion_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.add_column("silver_notice_line", sa.Column("line_bid_count", sa.Integer(), nullable=True))
    op.add_column("silver_notice_line", sa.Column("line_supplier_count", sa.Integer(), nullable=True))
    op.add_column("silver_notice_line", sa.Column("line_min_offer_amount", sa.Numeric(20, 6), nullable=True))
    op.add_column("silver_notice_line", sa.Column("line_max_offer_amount", sa.Numeric(20, 6), nullable=True))
    op.add_column("silver_notice_line", sa.Column("line_avg_offer_amount", sa.Numeric(20, 6), nullable=True))
    op.add_column("silver_notice_line", sa.Column("line_median_offer_amount", sa.Numeric(20, 6), nullable=True))
    op.add_column(
        "silver_notice_line",
        sa.Column("line_price_dispersion_ratio", sa.Numeric(20, 6), nullable=True),
    )

    op.add_column("silver_bid_submission", sa.Column("item_code", sa.Text(), nullable=True))
    op.add_column("silver_award_outcome", sa.Column("item_code", sa.Text(), nullable=True))

    op.add_column(
        "silver_purchase_order",
        sa.Column("days_order_creation_to_acceptance", sa.Integer(), nullable=True),
    )
    op.add_column(
        "silver_purchase_order",
        sa.Column("days_order_creation_to_cancellation", sa.Integer(), nullable=True),
    )
    op.add_column(
        "silver_purchase_order",
        sa.Column(
            "is_linked_to_notice_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column("silver_purchase_order", sa.Column("purchase_order_line_count", sa.Integer(), nullable=True))
    op.add_column(
        "silver_purchase_order",
        sa.Column("purchase_order_total_quantity", sa.Numeric(20, 6), nullable=True),
    )
    op.add_column(
        "silver_purchase_order",
        sa.Column("purchase_order_total_net_amount", sa.Numeric(20, 6), nullable=True),
    )
    op.add_column(
        "silver_purchase_order",
        sa.Column("purchase_order_unique_product_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("silver_purchase_order", "purchase_order_unique_product_count")
    op.drop_column("silver_purchase_order", "purchase_order_total_net_amount")
    op.drop_column("silver_purchase_order", "purchase_order_total_quantity")
    op.drop_column("silver_purchase_order", "purchase_order_line_count")
    op.drop_column("silver_purchase_order", "is_linked_to_notice_flag")
    op.drop_column("silver_purchase_order", "days_order_creation_to_cancellation")
    op.drop_column("silver_purchase_order", "days_order_creation_to_acceptance")

    op.drop_column("silver_award_outcome", "item_code")
    op.drop_column("silver_bid_submission", "item_code")

    op.drop_column("silver_notice_line", "line_price_dispersion_ratio")
    op.drop_column("silver_notice_line", "line_median_offer_amount")
    op.drop_column("silver_notice_line", "line_avg_offer_amount")
    op.drop_column("silver_notice_line", "line_max_offer_amount")
    op.drop_column("silver_notice_line", "line_min_offer_amount")
    op.drop_column("silver_notice_line", "line_supplier_count")
    op.drop_column("silver_notice_line", "line_bid_count")

    op.drop_column("silver_notice", "notice_awarded_to_order_conversion_flag")
    op.drop_column("silver_notice", "notice_purchase_order_count")
    op.drop_column("silver_notice", "notice_has_purchase_order_flag")
    op.drop_column("silver_notice", "notice_awarded_line_count")
    op.drop_column("silver_notice", "notice_selected_bid_count")
    op.drop_column("silver_notice", "notice_supplier_count")
    op.drop_column("silver_notice", "notice_bid_count")
    op.drop_column("silver_notice", "notice_line_count")
    op.drop_column("silver_notice", "has_physical_document_delivery_flag")
    op.drop_column("silver_notice", "has_site_visit_flag")
    op.drop_column("silver_notice", "has_extension_flag")
    op.drop_column("silver_notice", "hidden_budget_flag")
    op.drop_column("silver_notice", "multiple_stages_flag")
    op.drop_column("silver_notice", "requires_toma_razon_flag")
    op.drop_column("silver_notice", "is_private_tender_flag")
    op.drop_column("silver_notice", "is_public_tender_flag")
    op.drop_column("silver_notice", "has_missing_date_chain_flag")
    op.drop_column("silver_notice", "days_close_to_award")
    op.drop_column("silver_notice", "days_creation_to_close")
    op.drop_column("silver_notice", "days_publication_to_close")
