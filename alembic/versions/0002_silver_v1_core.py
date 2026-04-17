"""create silver v1 core tables

Revision ID: 0002_silver_v1_core
Revises: 0001_operational_and_bronze
Create Date: 2026-04-16 21:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_silver_v1_core"
down_revision: Union[str, None] = "0001_operational_and_bronze"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "silver_licitaciones",
        sa.Column("codigo_externo", sa.Text(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipo_adquisicion", sa.Text(), nullable=True),
        sa.Column("tipo_adquisicion_norm", sa.Text(), nullable=True),
        sa.Column("codigo_estado", sa.Integer(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=True),
        sa.Column("tipo_convocatoria", sa.Text(), nullable=True),
        sa.Column("moneda_adquisicion", sa.Text(), nullable=True),
        sa.Column("visibilidad_monto_raw", sa.Text(), nullable=True),
        sa.Column("monto_estimado", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("numero_oferentes", sa.Integer(), nullable=True),
        sa.Column("codigo_organismo", sa.Text(), nullable=True),
        sa.Column("nombre_organismo", sa.Text(), nullable=True),
        sa.Column("codigo_unidad", sa.Text(), nullable=True),
        sa.Column("nombre_unidad", sa.Text(), nullable=True),
        sa.Column("comuna_unidad", sa.Text(), nullable=True),
        sa.Column("region_unidad", sa.Text(), nullable=True),
        sa.Column("fecha_publicacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_cierre", sa.DateTime(), nullable=True),
        sa.Column("fecha_adjudicacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_estimada_adjudicacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=True),
        sa.Column("fecha_final", sa.DateTime(), nullable=True),
        sa.Column("cantidad_dias_licitacion", sa.Integer(), nullable=True),
        sa.Column("flag_licitacion_publica", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("flag_licitacion_privada", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("flag_licitacion_servicios", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("flag_menos_100_utm", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_elegible_mvp", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("codigo_externo"),
    )
    op.create_index(
        "ix_silver_licitaciones_estado",
        "silver_licitaciones",
        ["estado"],
        unique=False,
    )
    op.create_index(
        "ix_silver_licitaciones_fecha_publicacion",
        "silver_licitaciones",
        ["fecha_publicacion"],
        unique=False,
    )
    op.create_index(
        "ix_silver_licitaciones_is_elegible_mvp",
        "silver_licitaciones",
        ["is_elegible_mvp"],
        unique=False,
    )
    op.create_index(
        "ix_silver_licitaciones_tipo_adquisicion_norm",
        "silver_licitaciones",
        ["tipo_adquisicion_norm"],
        unique=False,
    )

    op.create_table(
        "silver_licitacion_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo_externo", sa.Text(), nullable=False),
        sa.Column("codigo_item", sa.Text(), nullable=False),
        sa.Column("correlativo", sa.Text(), nullable=True),
        sa.Column("codigo_producto_onu", sa.Text(), nullable=True),
        sa.Column("nombre_producto_generico", sa.Text(), nullable=True),
        sa.Column("nombre_linea_adquisicion", sa.Text(), nullable=True),
        sa.Column("descripcion_linea_adquisicion", sa.Text(), nullable=True),
        sa.Column("unidad_medida", sa.Text(), nullable=True),
        sa.Column("cantidad", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("rubro1", sa.Text(), nullable=True),
        sa.Column("rubro2", sa.Text(), nullable=True),
        sa.Column("rubro3", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["codigo_externo"], ["silver_licitaciones.codigo_externo"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_externo", "codigo_item", name="uq_silver_lic_item"),
    )
    op.create_index(
        "ix_silver_licitacion_items_codigo_externo",
        "silver_licitacion_items",
        ["codigo_externo"],
        unique=False,
    )
    op.create_index(
        "ix_silver_licitacion_items_codigo_producto_onu",
        "silver_licitacion_items",
        ["codigo_producto_onu"],
        unique=False,
    )

    op.create_table(
        "silver_ofertas",
        sa.Column("oferta_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("codigo_externo", sa.Text(), nullable=False),
        sa.Column("codigo_item", sa.Text(), nullable=True),
        sa.Column("correlativo", sa.Text(), nullable=True),
        sa.Column("codigo_proveedor", sa.Text(), nullable=True),
        sa.Column("rut_proveedor", sa.Text(), nullable=True),
        sa.Column("nombre_proveedor", sa.Text(), nullable=True),
        sa.Column("razon_social_proveedor", sa.Text(), nullable=True),
        sa.Column("estado_oferta", sa.Text(), nullable=True),
        sa.Column("nombre_oferta", sa.Text(), nullable=True),
        sa.Column("cantidad_ofertada", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("monto_unitario_oferta", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("valor_total_ofertado", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("oferta_seleccionada", sa.Boolean(), nullable=True),
        sa.Column("fecha_envio_oferta", sa.DateTime(), nullable=True),
        sa.Column("cantidad_adjudicada", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("monto_linea_adjudica", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("monto_estimado_adjudicado", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["codigo_externo"], ["silver_licitaciones.codigo_externo"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("oferta_key_sha256"),
    )
    op.create_index(
        "ix_silver_ofertas_codigo_externo",
        "silver_ofertas",
        ["codigo_externo"],
        unique=False,
    )
    op.create_index(
        "ix_silver_ofertas_codigo_proveedor",
        "silver_ofertas",
        ["codigo_proveedor"],
        unique=False,
    )
    op.create_index(
        "ix_silver_ofertas_rut_proveedor",
        "silver_ofertas",
        ["rut_proveedor"],
        unique=False,
    )

    op.create_table(
        "silver_ordenes_compra",
        sa.Column("codigo_oc", sa.Text(), nullable=False),
        sa.Column("id_oc_raw", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=True),
        sa.Column("descripcion_observaciones", sa.Text(), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=True),
        sa.Column("procedencia_oc", sa.Text(), nullable=True),
        sa.Column("es_trato_directo", sa.Boolean(), nullable=True),
        sa.Column("es_compra_agil", sa.Boolean(), nullable=True),
        sa.Column("codigo_tipo", sa.Text(), nullable=True),
        sa.Column("codigo_abreviado_tipo_oc", sa.Text(), nullable=True),
        sa.Column("descripcion_tipo_oc", sa.Text(), nullable=True),
        sa.Column("codigo_estado", sa.Text(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=True),
        sa.Column("codigo_estado_proveedor", sa.Text(), nullable=True),
        sa.Column("estado_proveedor", sa.Text(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_envio", sa.DateTime(), nullable=True),
        sa.Column("fecha_solicitud_cancelacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_aceptacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_cancelacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_ultima_modificacion", sa.DateTime(), nullable=True),
        sa.Column("tiene_items", sa.Boolean(), nullable=True),
        sa.Column("promedio_calificacion", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("cantidad_evaluacion", sa.Integer(), nullable=True),
        sa.Column("tipo_moneda_oc", sa.Text(), nullable=True),
        sa.Column("monto_total_oc", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("monto_total_oc_pesos_chilenos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("impuestos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("tipo_impuesto", sa.Text(), nullable=True),
        sa.Column("descuentos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("cargos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_neto_oc", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_cargos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_descuentos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_impuestos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("porcentaje_iva", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("codigo_licitacion", sa.Text(), nullable=True),
        sa.Column("codigo_convenio_marco", sa.Text(), nullable=True),
        sa.Column("has_codigo_licitacion", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("codigo_unidad_compra", sa.Text(), nullable=True),
        sa.Column("rut_unidad_compra", sa.Text(), nullable=True),
        sa.Column("unidad_compra", sa.Text(), nullable=True),
        sa.Column("codigo_organismo_publico", sa.Text(), nullable=True),
        sa.Column("organismo_publico", sa.Text(), nullable=True),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("actividad_comprador", sa.Text(), nullable=True),
        sa.Column("ciudad_unidad_compra", sa.Text(), nullable=True),
        sa.Column("region_unidad_compra", sa.Text(), nullable=True),
        sa.Column("pais_unidad_compra", sa.Text(), nullable=True),
        sa.Column("codigo_sucursal", sa.Text(), nullable=True),
        sa.Column("rut_sucursal", sa.Text(), nullable=True),
        sa.Column("sucursal", sa.Text(), nullable=True),
        sa.Column("codigo_proveedor", sa.Text(), nullable=True),
        sa.Column("nombre_proveedor", sa.Text(), nullable=True),
        sa.Column("actividad_proveedor", sa.Text(), nullable=True),
        sa.Column("comuna_proveedor", sa.Text(), nullable=True),
        sa.Column("region_proveedor", sa.Text(), nullable=True),
        sa.Column("pais_proveedor", sa.Text(), nullable=True),
        sa.Column("financiamiento", sa.Text(), nullable=True),
        sa.Column("pais", sa.Text(), nullable=True),
        sa.Column("tipo_despacho", sa.Text(), nullable=True),
        sa.Column("forma_pago", sa.Text(), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("codigo_oc"),
    )
    op.create_index(
        "ix_silver_ordenes_compra_estado",
        "silver_ordenes_compra",
        ["estado"],
        unique=False,
    )
    op.create_index(
        "ix_silver_ordenes_compra_fecha_envio",
        "silver_ordenes_compra",
        ["fecha_envio"],
        unique=False,
    )
    op.create_index(
        "ix_silver_ordenes_compra_codigo_licitacion",
        "silver_ordenes_compra",
        ["codigo_licitacion"],
        unique=False,
    )
    op.create_index(
        "ix_silver_ordenes_compra_codigo_proveedor",
        "silver_ordenes_compra",
        ["codigo_proveedor"],
        unique=False,
    )
    op.create_index(
        "ix_silver_ordenes_compra_codigo_unidad_compra",
        "silver_ordenes_compra",
        ["codigo_unidad_compra"],
        unique=False,
    )

    op.create_table(
        "silver_ordenes_compra_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo_oc", sa.Text(), nullable=False),
        sa.Column("id_item", sa.Text(), nullable=False),
        sa.Column("codigo_producto_onu", sa.Text(), nullable=True),
        sa.Column("codigo_categoria", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("nombre_producto_generico", sa.Text(), nullable=True),
        sa.Column("rubro_n1", sa.Text(), nullable=True),
        sa.Column("rubro_n2", sa.Text(), nullable=True),
        sa.Column("rubro_n3", sa.Text(), nullable=True),
        sa.Column("especificacion_comprador", sa.Text(), nullable=True),
        sa.Column("especificacion_proveedor", sa.Text(), nullable=True),
        sa.Column("cantidad", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("unidad_medida", sa.Text(), nullable=True),
        sa.Column("moneda_item", sa.Text(), nullable=True),
        sa.Column("precio_neto", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_cargos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_descuentos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_impuestos", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("total_linea_neto", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["codigo_oc"], ["silver_ordenes_compra.codigo_oc"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_oc", "id_item", name="uq_silver_oc_item"),
    )
    op.create_index(
        "ix_silver_ordenes_compra_items_codigo_oc",
        "silver_ordenes_compra_items",
        ["codigo_oc"],
        unique=False,
    )
    op.create_index(
        "ix_silver_ordenes_compra_items_codigo_producto_onu",
        "silver_ordenes_compra_items",
        ["codigo_producto_onu"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_silver_ordenes_compra_items_codigo_producto_onu",
        table_name="silver_ordenes_compra_items",
    )
    op.drop_index(
        "ix_silver_ordenes_compra_items_codigo_oc",
        table_name="silver_ordenes_compra_items",
    )
    op.drop_table("silver_ordenes_compra_items")

    op.drop_index("ix_silver_ordenes_compra_codigo_unidad_compra", table_name="silver_ordenes_compra")
    op.drop_index("ix_silver_ordenes_compra_codigo_proveedor", table_name="silver_ordenes_compra")
    op.drop_index("ix_silver_ordenes_compra_codigo_licitacion", table_name="silver_ordenes_compra")
    op.drop_index("ix_silver_ordenes_compra_fecha_envio", table_name="silver_ordenes_compra")
    op.drop_index("ix_silver_ordenes_compra_estado", table_name="silver_ordenes_compra")
    op.drop_table("silver_ordenes_compra")

    op.drop_index("ix_silver_ofertas_rut_proveedor", table_name="silver_ofertas")
    op.drop_index("ix_silver_ofertas_codigo_proveedor", table_name="silver_ofertas")
    op.drop_index("ix_silver_ofertas_codigo_externo", table_name="silver_ofertas")
    op.drop_table("silver_ofertas")

    op.drop_index("ix_silver_licitacion_items_codigo_producto_onu", table_name="silver_licitacion_items")
    op.drop_index("ix_silver_licitacion_items_codigo_externo", table_name="silver_licitacion_items")
    op.drop_table("silver_licitacion_items")

    op.drop_index("ix_silver_licitaciones_tipo_adquisicion_norm", table_name="silver_licitaciones")
    op.drop_index("ix_silver_licitaciones_is_elegible_mvp", table_name="silver_licitaciones")
    op.drop_index("ix_silver_licitaciones_fecha_publicacion", table_name="silver_licitaciones")
    op.drop_index("ix_silver_licitaciones_estado", table_name="silver_licitaciones")
    op.drop_table("silver_licitaciones")
