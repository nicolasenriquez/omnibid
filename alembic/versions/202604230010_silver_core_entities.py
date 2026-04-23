"""silver core entities

Revision ID: 202604230010_silver_core
Revises: 20260422172140_normalized_domain
Create Date: 2026-04-23 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202604230010_silver_core"
down_revision: Union[str, None] = "20260422172140_normalized_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "silver_notice",
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("external_notice_code", sa.Text(), nullable=True),
        sa.Column("notice_url", sa.Text(), nullable=True),
        sa.Column("notice_title", sa.Text(), nullable=True),
        sa.Column("notice_description_raw", sa.Text(), nullable=True),
        sa.Column("notice_description_clean", sa.Text(), nullable=True),
        sa.Column("procurement_method_name", sa.Text(), nullable=True),
        sa.Column("procurement_method_code", sa.Text(), nullable=True),
        sa.Column("notice_status_name", sa.Text(), nullable=True),
        sa.Column("notice_status_code", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.DateTime(), nullable=True),
        sa.Column("created_date", sa.DateTime(), nullable=True),
        sa.Column("close_date", sa.DateTime(), nullable=True),
        sa.Column("award_date", sa.DateTime(), nullable=True),
        sa.Column("estimated_award_date", sa.DateTime(), nullable=True),
        sa.Column("estimated_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("currency_code", sa.Text(), nullable=True),
        sa.Column("currency_name", sa.Text(), nullable=True),
        sa.Column("number_of_bidders_reported", sa.Integer(), nullable=True),
        sa.Column("complaint_count", sa.Integer(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("notice_id"),
    )
    op.create_index(
        "ix_silver_notice_publication_date",
        "silver_notice",
        ["publication_date"],
        unique=False,
    )
    op.create_index(
        "ix_silver_notice_status_name",
        "silver_notice",
        ["notice_status_name"],
        unique=False,
    )

    op.create_table(
        "silver_notice_line",
        sa.Column("notice_line_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Text(), nullable=True),
        sa.Column("item_code", sa.Text(), nullable=False),
        sa.Column("onu_product_code", sa.Text(), nullable=True),
        sa.Column("category_level_1", sa.Text(), nullable=True),
        sa.Column("category_level_2", sa.Text(), nullable=True),
        sa.Column("category_level_3", sa.Text(), nullable=True),
        sa.Column("generic_product_name", sa.Text(), nullable=True),
        sa.Column("line_name", sa.Text(), nullable=True),
        sa.Column("line_description_raw", sa.Text(), nullable=True),
        sa.Column("line_description_clean", sa.Text(), nullable=True),
        sa.Column("unit_of_measure", sa.Text(), nullable=True),
        sa.Column("quantity_requested", sa.Numeric(20, 6), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["notice_id"], ["silver_notice.notice_id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("notice_line_id"),
        sa.UniqueConstraint("notice_id", "item_code", name="uq_silver_notice_line_notice_item"),
    )
    op.create_index(
        "ix_silver_notice_line_notice_id",
        "silver_notice_line",
        ["notice_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_notice_line_onu_product_code",
        "silver_notice_line",
        ["onu_product_code"],
        unique=False,
    )

    op.create_table(
        "silver_bid_submission",
        sa.Column("bid_submission_id", sa.String(length=64), nullable=False),
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("notice_line_id", sa.BigInteger(), nullable=True),
        sa.Column("supplier_key", sa.Text(), nullable=True),
        sa.Column("supplier_branch_id", sa.Text(), nullable=True),
        sa.Column("offer_name", sa.Text(), nullable=True),
        sa.Column("offer_status", sa.Text(), nullable=True),
        sa.Column("offer_submission_date", sa.DateTime(), nullable=True),
        sa.Column("offered_quantity", sa.Numeric(20, 6), nullable=True),
        sa.Column("offer_currency_name", sa.Text(), nullable=True),
        sa.Column("unit_price_offered", sa.Numeric(20, 6), nullable=True),
        sa.Column("total_price_offered", sa.Numeric(20, 6), nullable=True),
        sa.Column("selected_offer_flag", sa.Boolean(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["notice_id"], ["silver_notice.notice_id"]),
        sa.ForeignKeyConstraint(["notice_line_id"], ["silver_notice_line.notice_line_id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("bid_submission_id"),
    )
    op.create_index(
        "ix_silver_bid_submission_notice_id",
        "silver_bid_submission",
        ["notice_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_bid_submission_supplier_key",
        "silver_bid_submission",
        ["supplier_key"],
        unique=False,
    )

    op.create_table(
        "silver_award_outcome",
        sa.Column("award_outcome_id", sa.String(length=64), nullable=False),
        sa.Column("bid_submission_id", sa.String(length=64), nullable=True),
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("notice_line_id", sa.BigInteger(), nullable=True),
        sa.Column("supplier_key", sa.Text(), nullable=True),
        sa.Column("selected_offer_flag", sa.Boolean(), nullable=True),
        sa.Column("awarded_quantity", sa.Numeric(20, 6), nullable=True),
        sa.Column("awarded_line_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("award_date", sa.DateTime(), nullable=True),
        sa.Column("award_status", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bid_submission_id"], ["silver_bid_submission.bid_submission_id"]),
        sa.ForeignKeyConstraint(["notice_id"], ["silver_notice.notice_id"]),
        sa.ForeignKeyConstraint(["notice_line_id"], ["silver_notice_line.notice_line_id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("award_outcome_id"),
    )
    op.create_index(
        "ix_silver_award_outcome_notice_id",
        "silver_award_outcome",
        ["notice_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_award_outcome_supplier_key",
        "silver_award_outcome",
        ["supplier_key"],
        unique=False,
    )

    op.create_table(
        "silver_purchase_order",
        sa.Column("purchase_order_id", sa.Text(), nullable=False),
        sa.Column("purchase_order_code", sa.Text(), nullable=True),
        sa.Column("purchase_order_url", sa.Text(), nullable=True),
        sa.Column("purchase_order_name", sa.Text(), nullable=True),
        sa.Column("purchase_order_description_raw", sa.Text(), nullable=True),
        sa.Column("purchase_order_description_clean", sa.Text(), nullable=True),
        sa.Column("purchase_order_type", sa.Text(), nullable=True),
        sa.Column("purchase_order_type_code", sa.Text(), nullable=True),
        sa.Column("purchase_order_status_code", sa.Text(), nullable=True),
        sa.Column("purchase_order_status_name", sa.Text(), nullable=True),
        sa.Column("supplier_status_code", sa.Text(), nullable=True),
        sa.Column("supplier_status_name", sa.Text(), nullable=True),
        sa.Column("order_created_at", sa.DateTime(), nullable=True),
        sa.Column("order_sent_at", sa.DateTime(), nullable=True),
        sa.Column("order_accepted_at", sa.DateTime(), nullable=True),
        sa.Column("order_cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("order_last_modified_at", sa.DateTime(), nullable=True),
        sa.Column("total_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("net_total_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("tax_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("discount_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("charge_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("currency_code", sa.Text(), nullable=True),
        sa.Column("currency_name", sa.Text(), nullable=True),
        sa.Column("supplier_key", sa.Text(), nullable=True),
        sa.Column("supplier_branch_id", sa.Text(), nullable=True),
        sa.Column("linked_notice_id", sa.Text(), nullable=True),
        sa.Column(
            "is_direct_award_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_agile_purchase_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "has_items_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("purchase_order_id"),
    )
    op.create_index(
        "ix_silver_purchase_order_linked_notice_id",
        "silver_purchase_order",
        ["linked_notice_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_purchase_order_supplier_key",
        "silver_purchase_order",
        ["supplier_key"],
        unique=False,
    )
    op.create_index(
        "ix_silver_purchase_order_status_name",
        "silver_purchase_order",
        ["purchase_order_status_name"],
        unique=False,
    )

    op.create_table(
        "silver_purchase_order_line",
        sa.Column("purchase_order_line_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("purchase_order_id", sa.Text(), nullable=False),
        sa.Column("line_item_id", sa.Text(), nullable=False),
        sa.Column("linked_notice_id", sa.Text(), nullable=True),
        sa.Column("onu_product_code", sa.Text(), nullable=True),
        sa.Column("category_code", sa.Text(), nullable=True),
        sa.Column("category_name", sa.Text(), nullable=True),
        sa.Column("category_level_1", sa.Text(), nullable=True),
        sa.Column("category_level_2", sa.Text(), nullable=True),
        sa.Column("category_level_3", sa.Text(), nullable=True),
        sa.Column("generic_product_name", sa.Text(), nullable=True),
        sa.Column("buyer_item_spec_raw", sa.Text(), nullable=True),
        sa.Column("buyer_item_spec_clean", sa.Text(), nullable=True),
        sa.Column("supplier_item_spec_raw", sa.Text(), nullable=True),
        sa.Column("supplier_item_spec_clean", sa.Text(), nullable=True),
        sa.Column("quantity_ordered", sa.Numeric(20, 6), nullable=True),
        sa.Column("unit_of_measure", sa.Text(), nullable=True),
        sa.Column("line_currency", sa.Text(), nullable=True),
        sa.Column("unit_net_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("line_net_total", sa.Numeric(20, 6), nullable=True),
        sa.Column("line_tax_total", sa.Numeric(20, 6), nullable=True),
        sa.Column("line_discount_total", sa.Numeric(20, 6), nullable=True),
        sa.Column("line_charge_total", sa.Numeric(20, 6), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["silver_purchase_order.purchase_order_id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("purchase_order_line_id"),
        sa.UniqueConstraint(
            "purchase_order_id",
            "line_item_id",
            name="uq_silver_purchase_order_line_order_item",
        ),
    )
    op.create_index(
        "ix_silver_purchase_order_line_order_id",
        "silver_purchase_order_line",
        ["purchase_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_purchase_order_line_linked_notice_id",
        "silver_purchase_order_line",
        ["linked_notice_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_silver_purchase_order_line_linked_notice_id",
        table_name="silver_purchase_order_line",
    )
    op.drop_index("ix_silver_purchase_order_line_order_id", table_name="silver_purchase_order_line")
    op.drop_table("silver_purchase_order_line")

    op.drop_index("ix_silver_purchase_order_status_name", table_name="silver_purchase_order")
    op.drop_index("ix_silver_purchase_order_supplier_key", table_name="silver_purchase_order")
    op.drop_index("ix_silver_purchase_order_linked_notice_id", table_name="silver_purchase_order")
    op.drop_table("silver_purchase_order")

    op.drop_index("ix_silver_award_outcome_supplier_key", table_name="silver_award_outcome")
    op.drop_index("ix_silver_award_outcome_notice_id", table_name="silver_award_outcome")
    op.drop_table("silver_award_outcome")

    op.drop_index("ix_silver_bid_submission_supplier_key", table_name="silver_bid_submission")
    op.drop_index("ix_silver_bid_submission_notice_id", table_name="silver_bid_submission")
    op.drop_table("silver_bid_submission")

    op.drop_index("ix_silver_notice_line_onu_product_code", table_name="silver_notice_line")
    op.drop_index("ix_silver_notice_line_notice_id", table_name="silver_notice_line")
    op.drop_table("silver_notice_line")

    op.drop_index("ix_silver_notice_status_name", table_name="silver_notice")
    op.drop_index("ix_silver_notice_publication_date", table_name="silver_notice")
    op.drop_table("silver_notice")
