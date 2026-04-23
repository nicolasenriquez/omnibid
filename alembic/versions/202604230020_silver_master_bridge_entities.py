"""silver master and bridge entities

Revision ID: 202604230020_silver_master
Revises: 202604230010_silver_core
Create Date: 2026-04-23 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202604230020_silver_master"
down_revision: Union[str, None] = "202604230010_silver_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "silver_buying_org",
        sa.Column("buying_org_id", sa.Text(), nullable=False),
        sa.Column("buying_org_name", sa.Text(), nullable=True),
        sa.Column("sector_name", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.PrimaryKeyConstraint("buying_org_id"),
    )
    op.create_index(
        "ix_silver_buying_org_name",
        "silver_buying_org",
        ["buying_org_name"],
        unique=False,
    )

    op.create_table(
        "silver_contracting_unit",
        sa.Column("contracting_unit_id", sa.Text(), nullable=False),
        sa.Column("buying_org_id", sa.Text(), nullable=False),
        sa.Column("unit_rut", sa.Text(), nullable=True),
        sa.Column("unit_name", sa.Text(), nullable=True),
        sa.Column("unit_address", sa.Text(), nullable=True),
        sa.Column("unit_commune", sa.Text(), nullable=True),
        sa.Column("unit_region", sa.Text(), nullable=True),
        sa.Column("unit_city", sa.Text(), nullable=True),
        sa.Column("unit_country", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["buying_org_id"], ["silver_buying_org.buying_org_id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("contracting_unit_id"),
    )
    op.create_index(
        "ix_silver_contracting_unit_buying_org_id",
        "silver_contracting_unit",
        ["buying_org_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_contracting_unit_unit_rut",
        "silver_contracting_unit",
        ["unit_rut"],
        unique=False,
    )

    op.create_table(
        "silver_supplier",
        sa.Column("supplier_id", sa.Text(), nullable=False),
        sa.Column("supplier_branch_id", sa.Text(), nullable=True),
        sa.Column("supplier_rut", sa.Text(), nullable=True),
        sa.Column("supplier_trade_name", sa.Text(), nullable=True),
        sa.Column("supplier_legal_name", sa.Text(), nullable=True),
        sa.Column("supplier_activity", sa.Text(), nullable=True),
        sa.Column("supplier_commune", sa.Text(), nullable=True),
        sa.Column("supplier_region", sa.Text(), nullable=True),
        sa.Column("supplier_country", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.PrimaryKeyConstraint("supplier_id"),
    )
    op.create_index(
        "ix_silver_supplier_supplier_rut",
        "silver_supplier",
        ["supplier_rut"],
        unique=False,
    )
    op.create_index(
        "ix_silver_supplier_supplier_branch_id",
        "silver_supplier",
        ["supplier_branch_id"],
        unique=False,
    )

    op.create_table(
        "silver_category_ref",
        sa.Column("category_ref_id", sa.Text(), nullable=False),
        sa.Column("onu_product_code", sa.Text(), nullable=True),
        sa.Column("category_code", sa.Text(), nullable=True),
        sa.Column("category_name", sa.Text(), nullable=True),
        sa.Column("category_level_1", sa.Text(), nullable=True),
        sa.Column("category_level_2", sa.Text(), nullable=True),
        sa.Column("category_level_3", sa.Text(), nullable=True),
        sa.Column("generic_product_name_canonical", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.PrimaryKeyConstraint("category_ref_id"),
    )
    op.create_index(
        "ix_silver_category_ref_onu_product_code",
        "silver_category_ref",
        ["onu_product_code"],
        unique=False,
    )
    op.create_index(
        "ix_silver_category_ref_category_code",
        "silver_category_ref",
        ["category_code"],
        unique=False,
    )

    op.create_table(
        "silver_notice_purchase_order_link",
        sa.Column("notice_purchase_order_link_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("purchase_order_id", sa.Text(), nullable=False),
        sa.Column("link_type", sa.Text(), nullable=False),
        sa.Column("link_confidence", sa.Numeric(10, 6), nullable=True),
        sa.Column("source_system", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["purchase_order_id"], ["silver_purchase_order.purchase_order_id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("notice_purchase_order_link_id"),
        sa.UniqueConstraint(
            "notice_id",
            "purchase_order_id",
            "link_type",
            name="uq_silver_notice_purchase_order_link",
        ),
    )
    op.create_index(
        "ix_silver_notice_purchase_order_link_notice_id",
        "silver_notice_purchase_order_link",
        ["notice_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_notice_purchase_order_link_purchase_order_id",
        "silver_notice_purchase_order_link",
        ["purchase_order_id"],
        unique=False,
    )

    op.create_table(
        "silver_supplier_participation",
        sa.Column("supplier_participation_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("supplier_id", sa.Text(), nullable=False),
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("notice_line_id", sa.BigInteger(), nullable=True),
        sa.Column("bid_submission_id", sa.String(length=64), nullable=True),
        sa.Column("award_outcome_id", sa.String(length=64), nullable=True),
        sa.Column("purchase_order_line_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "was_selected_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "was_materialized_in_purchase_order_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["supplier_id"], ["silver_supplier.supplier_id"]),
        sa.ForeignKeyConstraint(["notice_id"], ["silver_notice.notice_id"]),
        sa.ForeignKeyConstraint(["notice_line_id"], ["silver_notice_line.notice_line_id"]),
        sa.ForeignKeyConstraint(["bid_submission_id"], ["silver_bid_submission.bid_submission_id"]),
        sa.ForeignKeyConstraint(["award_outcome_id"], ["silver_award_outcome.award_outcome_id"]),
        sa.ForeignKeyConstraint(["purchase_order_line_id"], ["silver_purchase_order_line.purchase_order_line_id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("supplier_participation_id"),
        sa.UniqueConstraint(
            "supplier_id",
            "notice_id",
            name="uq_silver_supplier_participation_supplier_notice",
        ),
    )
    op.create_index(
        "ix_silver_supplier_participation_supplier_id",
        "silver_supplier_participation",
        ["supplier_id"],
        unique=False,
    )
    op.create_index(
        "ix_silver_supplier_participation_notice_id",
        "silver_supplier_participation",
        ["notice_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_silver_supplier_participation_notice_id",
        table_name="silver_supplier_participation",
    )
    op.drop_index(
        "ix_silver_supplier_participation_supplier_id",
        table_name="silver_supplier_participation",
    )
    op.drop_table("silver_supplier_participation")

    op.drop_index(
        "ix_silver_notice_purchase_order_link_purchase_order_id",
        table_name="silver_notice_purchase_order_link",
    )
    op.drop_index(
        "ix_silver_notice_purchase_order_link_notice_id",
        table_name="silver_notice_purchase_order_link",
    )
    op.drop_table("silver_notice_purchase_order_link")

    op.drop_index("ix_silver_category_ref_category_code", table_name="silver_category_ref")
    op.drop_index("ix_silver_category_ref_onu_product_code", table_name="silver_category_ref")
    op.drop_table("silver_category_ref")

    op.drop_index("ix_silver_supplier_supplier_branch_id", table_name="silver_supplier")
    op.drop_index("ix_silver_supplier_supplier_rut", table_name="silver_supplier")
    op.drop_table("silver_supplier")

    op.drop_index("ix_silver_contracting_unit_unit_rut", table_name="silver_contracting_unit")
    op.drop_index(
        "ix_silver_contracting_unit_buying_org_id",
        table_name="silver_contracting_unit",
    )
    op.drop_table("silver_contracting_unit")

    op.drop_index("ix_silver_buying_org_name", table_name="silver_buying_org")
    op.drop_table("silver_buying_org")
