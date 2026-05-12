"""create mercado_publico_notice_item_snapshot table

Revision ID: 2026051201
Revises: 2026051200
Create Date: 2026-05-12 00:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "2026051201"
down_revision: Union[str, None] = "2026051200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mercado_publico_notice_item_snapshot",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pipeline_run_id", UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("api_source_request.id"), nullable=False),
        sa.Column("payload_id", UUID(as_uuid=True), sa.ForeignKey("api_source_payload.id"), nullable=False),
        sa.Column("external_notice_code", sa.Text(), nullable=False),
        sa.Column("item_correlative", sa.Integer(), nullable=True),
        sa.Column("codigo_producto", sa.Text(), nullable=True),
        sa.Column("codigo_categoria", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("nombre_producto", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("unidad_medida", sa.Text(), nullable=True),
        sa.Column("cantidad", sa.Text(), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_mp_notice_item_snapshot_external_notice_code",
        "mercado_publico_notice_item_snapshot",
        ["external_notice_code"],
        unique=False,
    )
    op.create_index(
        "ix_mp_notice_item_snapshot_payload_id",
        "mercado_publico_notice_item_snapshot",
        ["payload_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_mp_notice_item_snapshot_payload_notice_item",
        "mercado_publico_notice_item_snapshot",
        ["payload_id", "external_notice_code", "item_correlative"],
    )


def downgrade() -> None:
    op.drop_table("mercado_publico_notice_item_snapshot")
