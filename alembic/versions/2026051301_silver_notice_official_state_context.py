"""add official state and source context columns to silver_notice

Revision ID: 2026051301
Revises: 2026051201
Create Date: 2026-05-13 01:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026051301"
down_revision: Union[str, None] = "2026051201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("silver_notice", sa.Column("mp_estado_codigo", sa.Integer(), nullable=True))
    op.add_column("silver_notice", sa.Column("mp_estado_nombre", sa.Text(), nullable=True))
    op.add_column("silver_notice", sa.Column("mp_estado_canonical", sa.Text(), nullable=True))
    op.add_column("silver_notice", sa.Column("data_source_kind", sa.Text(), nullable=True))
    op.add_column("silver_notice", sa.Column("availability_context", sa.Text(), nullable=True))
    op.create_index(
        "ix_silver_notice_mp_estado_canonical",
        "silver_notice",
        ["mp_estado_canonical"],
        unique=False,
    )
    op.create_index(
        "ix_silver_notice_data_source_kind",
        "silver_notice",
        ["data_source_kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_silver_notice_data_source_kind", table_name="silver_notice")
    op.drop_index("ix_silver_notice_mp_estado_canonical", table_name="silver_notice")
    op.drop_column("silver_notice", "availability_context")
    op.drop_column("silver_notice", "data_source_kind")
    op.drop_column("silver_notice", "mp_estado_canonical")
    op.drop_column("silver_notice", "mp_estado_nombre")
    op.drop_column("silver_notice", "mp_estado_codigo")
