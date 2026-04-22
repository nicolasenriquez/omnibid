"""add dataset summary snapshots table

Revision ID: 0005_dataset_summary_snapshots
Revises: 0004_rename_raw_norm_tables
Create Date: 2026-04-22 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_dataset_summary_snapshots"
down_revision: Union[str, None] = "0004_rename_raw_norm_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_summary_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("refresh_mode", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'success'"), nullable=False),
        sa.Column("source_files_count", sa.BigInteger(), nullable=False),
        sa.Column("raw_licitaciones_count", sa.BigInteger(), nullable=False),
        sa.Column("raw_ordenes_compra_count", sa.BigInteger(), nullable=False),
        sa.Column("normalized_licitaciones_count", sa.BigInteger(), nullable=False),
        sa.Column("normalized_licitacion_items_count", sa.BigInteger(), nullable=False),
        sa.Column("normalized_ofertas_count", sa.BigInteger(), nullable=False),
        sa.Column("normalized_ordenes_compra_count", sa.BigInteger(), nullable=False),
        sa.Column("normalized_ordenes_compra_items_count", sa.BigInteger(), nullable=False),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dataset_summary_snapshots_generated_at",
        "dataset_summary_snapshots",
        ["generated_at"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_summary_snapshots_status_generated_at",
        "dataset_summary_snapshots",
        ["status", "generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_summary_snapshots_status_generated_at", table_name="dataset_summary_snapshots")
    op.drop_index("ix_dataset_summary_snapshots_generated_at", table_name="dataset_summary_snapshots")
    op.drop_table("dataset_summary_snapshots")
