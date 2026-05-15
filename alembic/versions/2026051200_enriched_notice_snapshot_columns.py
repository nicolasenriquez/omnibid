"""enriched notice snapshot columns

Revision ID: 2026051200
Revises: 202605091540_mp_api_hardening
Create Date: 2026-05-12 00:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026051200"
down_revision: Union[str, None] = "202605091540_mp_api_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mercado_publico_notice_snapshot", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("buyer_unit_address", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("buyer_unit_commune", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("buyer_unit_region", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("buyer_user_rut", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("buyer_user_code", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("buyer_user_name", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("buyer_user_position", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("created_date", sa.Date(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("estimated_award_date", sa.Date(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("award_date", sa.Date(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("tipo", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("codigo_tipo", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("tipo_convocatoria", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("days_to_close", sa.Integer(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("claim_count", sa.Integer(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("funding_source", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("visibility_amount", sa.Text(), nullable=True))
    op.add_column("mercado_publico_notice_snapshot", sa.Column("api_completeness_level", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("mercado_publico_notice_snapshot", "api_completeness_level")
    op.drop_column("mercado_publico_notice_snapshot", "visibility_amount")
    op.drop_column("mercado_publico_notice_snapshot", "funding_source")
    op.drop_column("mercado_publico_notice_snapshot", "claim_count")
    op.drop_column("mercado_publico_notice_snapshot", "days_to_close")
    op.drop_column("mercado_publico_notice_snapshot", "tipo_convocatoria")
    op.drop_column("mercado_publico_notice_snapshot", "codigo_tipo")
    op.drop_column("mercado_publico_notice_snapshot", "tipo")
    op.drop_column("mercado_publico_notice_snapshot", "award_date")
    op.drop_column("mercado_publico_notice_snapshot", "estimated_award_date")
    op.drop_column("mercado_publico_notice_snapshot", "created_date")
    op.drop_column("mercado_publico_notice_snapshot", "buyer_user_position")
    op.drop_column("mercado_publico_notice_snapshot", "buyer_user_name")
    op.drop_column("mercado_publico_notice_snapshot", "buyer_user_code")
    op.drop_column("mercado_publico_notice_snapshot", "buyer_user_rut")
    op.drop_column("mercado_publico_notice_snapshot", "buyer_unit_region")
    op.drop_column("mercado_publico_notice_snapshot", "buyer_unit_commune")
    op.drop_column("mercado_publico_notice_snapshot", "buyer_unit_address")
    op.drop_column("mercado_publico_notice_snapshot", "description")
