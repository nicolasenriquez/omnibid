"""silver text annotation entities

Revision ID: 202604230040_silver_text_ann
Revises: 202604230030_silver_enrichment
Create Date: 2026-04-23 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202604230040_silver_text_ann"
down_revision: Union[str, None] = "202604230030_silver_enrichment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "silver_notice_text_ann",
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("nlp_version", sa.Text(), nullable=False),
        sa.Column("corpus_scope", sa.Text(), nullable=False),
        sa.Column("language_detected", sa.Text(), nullable=True),
        sa.Column("normalized_tokens_json", sa.JSON(), nullable=True),
        sa.Column("top_ngrams_json", sa.JSON(), nullable=True),
        sa.Column("keyword_flags_json", sa.JSON(), nullable=True),
        sa.Column("domain_tags_json", sa.JSON(), nullable=True),
        sa.Column("semantic_category_label", sa.Text(), nullable=True),
        sa.Column("tfidf_artifact_ref", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("notice_id", "nlp_version"),
    )
    op.create_index(
        "ix_silver_notice_text_ann_semantic_category",
        "silver_notice_text_ann",
        ["semantic_category_label"],
        unique=False,
    )

    op.create_table(
        "silver_notice_line_text_ann",
        sa.Column("notice_id", sa.Text(), nullable=False),
        sa.Column("item_code", sa.Text(), nullable=False),
        sa.Column("nlp_version", sa.Text(), nullable=False),
        sa.Column("corpus_scope", sa.Text(), nullable=False),
        sa.Column("language_detected", sa.Text(), nullable=True),
        sa.Column("normalized_tokens_json", sa.JSON(), nullable=True),
        sa.Column("top_ngrams_json", sa.JSON(), nullable=True),
        sa.Column("keyword_flags_json", sa.JSON(), nullable=True),
        sa.Column("domain_tags_json", sa.JSON(), nullable=True),
        sa.Column("semantic_category_label", sa.Text(), nullable=True),
        sa.Column("tfidf_artifact_ref", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["notice_id", "item_code"],
            ["silver_notice_line.notice_id", "silver_notice_line.item_code"],
        ),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("notice_id", "item_code", "nlp_version"),
    )
    op.create_index(
        "ix_silver_notice_line_text_ann_semantic_category",
        "silver_notice_line_text_ann",
        ["semantic_category_label"],
        unique=False,
    )

    op.create_table(
        "silver_purchase_order_line_text_ann",
        sa.Column("purchase_order_id", sa.Text(), nullable=False),
        sa.Column("line_item_id", sa.Text(), nullable=False),
        sa.Column("nlp_version", sa.Text(), nullable=False),
        sa.Column("corpus_scope", sa.Text(), nullable=False),
        sa.Column("language_detected", sa.Text(), nullable=True),
        sa.Column("normalized_tokens_json", sa.JSON(), nullable=True),
        sa.Column("top_ngrams_json", sa.JSON(), nullable=True),
        sa.Column("buyer_spec_tags_json", sa.JSON(), nullable=True),
        sa.Column("supplier_spec_tags_json", sa.JSON(), nullable=True),
        sa.Column("semantic_category_label", sa.Text(), nullable=True),
        sa.Column("tfidf_artifact_ref", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["purchase_order_id", "line_item_id"],
            [
                "silver_purchase_order_line.purchase_order_id",
                "silver_purchase_order_line.line_item_id",
            ],
        ),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("purchase_order_id", "line_item_id", "nlp_version"),
    )
    op.create_index(
        "ix_silver_purchase_order_line_text_ann_semantic_category",
        "silver_purchase_order_line_text_ann",
        ["semantic_category_label"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_silver_purchase_order_line_text_ann_semantic_category",
        table_name="silver_purchase_order_line_text_ann",
    )
    op.drop_table("silver_purchase_order_line_text_ann")

    op.drop_index(
        "ix_silver_notice_line_text_ann_semantic_category",
        table_name="silver_notice_line_text_ann",
    )
    op.drop_table("silver_notice_line_text_ann")

    op.drop_index(
        "ix_silver_notice_text_ann_semantic_category",
        table_name="silver_notice_text_ann",
    )
    op.drop_table("silver_notice_text_ann")
