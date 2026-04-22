"""normalized domain entities

Revision ID: 20260422172140_normalized_domain
Revises: 0005_dataset_summary_snapshots
Create Date: 2026-04-22 17:21:42.009610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260422172140_normalized_domain'
down_revision: Union[str, None] = '0005_dataset_summary_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "normalized_buyers",
        sa.Column("buyer_key", sa.Text(), nullable=False),
        sa.Column("codigo_unidad_compra", sa.Text(), nullable=False),
        sa.Column("rut_unidad_compra", sa.Text(), nullable=True),
        sa.Column("unidad_compra", sa.Text(), nullable=True),
        sa.Column("codigo_organismo_publico", sa.Text(), nullable=True),
        sa.Column("organismo_publico", sa.Text(), nullable=True),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("actividad_comprador", sa.Text(), nullable=True),
        sa.Column("ciudad_unidad_compra", sa.Text(), nullable=True),
        sa.Column("region_unidad_compra", sa.Text(), nullable=True),
        sa.Column("pais_unidad_compra", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("buyer_key"),
    )
    op.create_index(
        "ix_normalized_buyers_codigo_unidad_compra",
        "normalized_buyers",
        ["codigo_unidad_compra"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_buyers_codigo_organismo_publico",
        "normalized_buyers",
        ["codigo_organismo_publico"],
        unique=False,
    )

    op.create_table(
        "normalized_suppliers",
        sa.Column("supplier_key", sa.Text(), nullable=False),
        sa.Column("codigo_proveedor", sa.Text(), nullable=True),
        sa.Column("rut_proveedor", sa.Text(), nullable=True),
        sa.Column("nombre_proveedor", sa.Text(), nullable=True),
        sa.Column("razon_social_proveedor", sa.Text(), nullable=True),
        sa.Column("actividad_proveedor", sa.Text(), nullable=True),
        sa.Column("comuna_proveedor", sa.Text(), nullable=True),
        sa.Column("region_proveedor", sa.Text(), nullable=True),
        sa.Column("pais_proveedor", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("supplier_key"),
    )
    op.create_index(
        "ix_normalized_suppliers_codigo_proveedor",
        "normalized_suppliers",
        ["codigo_proveedor"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_suppliers_rut_proveedor",
        "normalized_suppliers",
        ["rut_proveedor"],
        unique=False,
    )

    op.create_table(
        "normalized_categories",
        sa.Column("category_key", sa.Text(), nullable=False),
        sa.Column("codigo_categoria", sa.Text(), nullable=False),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("rubro_n1", sa.Text(), nullable=True),
        sa.Column("rubro_n2", sa.Text(), nullable=True),
        sa.Column("rubro_n3", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("category_key"),
    )
    op.create_index(
        "ix_normalized_categories_codigo_categoria",
        "normalized_categories",
        ["codigo_categoria"],
        unique=False,
    )

    op.add_column("normalized_ordenes_compra", sa.Column("buyer_key", sa.Text(), nullable=True))
    op.add_column("normalized_ordenes_compra", sa.Column("supplier_key", sa.Text(), nullable=True))
    op.add_column("normalized_ofertas", sa.Column("supplier_key", sa.Text(), nullable=True))
    op.add_column("normalized_ordenes_compra_items", sa.Column("category_key", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_normalized_ordenes_compra_buyer_key",
        "normalized_ordenes_compra",
        "normalized_buyers",
        ["buyer_key"],
        ["buyer_key"],
    )
    op.create_foreign_key(
        "fk_normalized_ordenes_compra_supplier_key",
        "normalized_ordenes_compra",
        "normalized_suppliers",
        ["supplier_key"],
        ["supplier_key"],
    )
    op.create_foreign_key(
        "fk_normalized_ofertas_supplier_key",
        "normalized_ofertas",
        "normalized_suppliers",
        ["supplier_key"],
        ["supplier_key"],
    )
    op.create_foreign_key(
        "fk_normalized_ordenes_compra_items_category_key",
        "normalized_ordenes_compra_items",
        "normalized_categories",
        ["category_key"],
        ["category_key"],
    )

    op.create_index(
        "ix_normalized_ordenes_compra_buyer_key",
        "normalized_ordenes_compra",
        ["buyer_key"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_ordenes_compra_supplier_key",
        "normalized_ordenes_compra",
        ["supplier_key"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_ofertas_supplier_key",
        "normalized_ofertas",
        ["supplier_key"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_ordenes_compra_items_category_key",
        "normalized_ordenes_compra_items",
        ["category_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_normalized_ordenes_compra_items_category_key", table_name="normalized_ordenes_compra_items")
    op.drop_index("ix_normalized_ofertas_supplier_key", table_name="normalized_ofertas")
    op.drop_index("ix_normalized_ordenes_compra_supplier_key", table_name="normalized_ordenes_compra")
    op.drop_index("ix_normalized_ordenes_compra_buyer_key", table_name="normalized_ordenes_compra")

    op.drop_constraint(
        "fk_normalized_ordenes_compra_items_category_key",
        "normalized_ordenes_compra_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_normalized_ofertas_supplier_key",
        "normalized_ofertas",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_normalized_ordenes_compra_supplier_key",
        "normalized_ordenes_compra",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_normalized_ordenes_compra_buyer_key",
        "normalized_ordenes_compra",
        type_="foreignkey",
    )

    op.drop_column("normalized_ordenes_compra_items", "category_key")
    op.drop_column("normalized_ofertas", "supplier_key")
    op.drop_column("normalized_ordenes_compra", "supplier_key")
    op.drop_column("normalized_ordenes_compra", "buyer_key")

    op.drop_index("ix_normalized_categories_codigo_categoria", table_name="normalized_categories")
    op.drop_table("normalized_categories")
    op.drop_index("ix_normalized_suppliers_rut_proveedor", table_name="normalized_suppliers")
    op.drop_index("ix_normalized_suppliers_codigo_proveedor", table_name="normalized_suppliers")
    op.drop_table("normalized_suppliers")
    op.drop_index("ix_normalized_buyers_codigo_organismo_publico", table_name="normalized_buyers")
    op.drop_index("ix_normalized_buyers_codigo_unidad_compra", table_name="normalized_buyers")
    op.drop_table("normalized_buyers")
