"""rename bronze/silver tables to raw/normalized

Revision ID: 0004_rename_raw_norm_tables
Revises: 0003_silver_oc_compat_patch
Create Date: 2026-04-17 13:00:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_rename_raw_norm_tables"
down_revision: Union[str, None] = "0003_silver_oc_compat_patch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_if_exists(command: str) -> None:
    op.execute(command)


def upgrade() -> None:
    # Raw layer
    _rename_if_exists("ALTER TABLE bronze_licitaciones_raw RENAME TO raw_licitaciones")
    _rename_if_exists("ALTER TABLE bronze_ordenes_compra_raw RENAME TO raw_ordenes_compra")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_bronze_licitaciones_raw_codigo_externo RENAME TO ix_raw_licitaciones_codigo_externo")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_bronze_ordenes_compra_raw_codigo_oc RENAME TO ix_raw_ordenes_compra_codigo_oc")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_bronze_ordenes_compra_raw_codigo_licitacion RENAME TO ix_raw_ordenes_compra_codigo_licitacion")
    _rename_if_exists("ALTER TABLE raw_licitaciones RENAME CONSTRAINT uq_bronze_lic_raw_file_row TO uq_raw_lic_raw_file_row")
    _rename_if_exists("ALTER TABLE raw_ordenes_compra RENAME CONSTRAINT uq_bronze_oc_raw_file_row TO uq_raw_oc_raw_file_row")
    _rename_if_exists("ALTER SEQUENCE IF EXISTS bronze_licitaciones_raw_id_seq RENAME TO raw_licitaciones_id_seq")
    _rename_if_exists("ALTER SEQUENCE IF EXISTS bronze_ordenes_compra_raw_id_seq RENAME TO raw_ordenes_compra_id_seq")

    # Normalized layer
    _rename_if_exists("ALTER TABLE silver_licitaciones RENAME TO normalized_licitaciones")
    _rename_if_exists("ALTER TABLE silver_licitacion_items RENAME TO normalized_licitacion_items")
    _rename_if_exists("ALTER TABLE silver_ofertas RENAME TO normalized_ofertas")
    _rename_if_exists("ALTER TABLE silver_ordenes_compra RENAME TO normalized_ordenes_compra")
    _rename_if_exists("ALTER TABLE silver_ordenes_compra_items RENAME TO normalized_ordenes_compra_items")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_licitaciones_estado RENAME TO ix_normalized_licitaciones_estado")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_licitaciones_fecha_publicacion RENAME TO ix_normalized_licitaciones_fecha_publicacion")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_licitaciones_is_elegible_mvp RENAME TO ix_normalized_licitaciones_is_elegible_mvp")
    _rename_if_exists(
        "ALTER INDEX IF EXISTS ix_silver_licitaciones_tipo_adquisicion_norm "
        "RENAME TO ix_normalized_licitaciones_tipo_adquisicion_norm"
    )
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_licitacion_items_codigo_externo RENAME TO ix_normalized_licitacion_items_codigo_externo")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_licitacion_items_codigo_producto_onu RENAME TO ix_normalized_licitacion_items_codigo_producto_onu")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ofertas_codigo_externo RENAME TO ix_normalized_ofertas_codigo_externo")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ofertas_codigo_proveedor RENAME TO ix_normalized_ofertas_codigo_proveedor")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ofertas_rut_proveedor RENAME TO ix_normalized_ofertas_rut_proveedor")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ordenes_compra_estado RENAME TO ix_normalized_ordenes_compra_estado")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ordenes_compra_fecha_envio RENAME TO ix_normalized_ordenes_compra_fecha_envio")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ordenes_compra_codigo_licitacion RENAME TO ix_normalized_ordenes_compra_codigo_licitacion")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ordenes_compra_codigo_proveedor RENAME TO ix_normalized_ordenes_compra_codigo_proveedor")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ordenes_compra_codigo_unidad_compra RENAME TO ix_normalized_ordenes_compra_codigo_unidad_compra")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ordenes_compra_items_codigo_oc RENAME TO ix_normalized_ordenes_compra_items_codigo_oc")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_silver_ordenes_compra_items_codigo_producto_onu RENAME TO ix_normalized_ordenes_compra_items_codigo_producto_onu")
    _rename_if_exists("ALTER TABLE normalized_licitacion_items RENAME CONSTRAINT uq_silver_lic_item TO uq_normalized_lic_item")
    _rename_if_exists("ALTER TABLE normalized_ordenes_compra_items RENAME CONSTRAINT uq_silver_oc_item TO uq_normalized_oc_item")


def downgrade() -> None:
    # Reverse the table, index, sequence, and constraint renames.
    _rename_if_exists("ALTER TABLE normalized_licitaciones RENAME TO silver_licitaciones")
    _rename_if_exists("ALTER TABLE normalized_licitacion_items RENAME TO silver_licitacion_items")
    _rename_if_exists("ALTER TABLE normalized_ofertas RENAME TO silver_ofertas")
    _rename_if_exists("ALTER TABLE normalized_ordenes_compra RENAME TO silver_ordenes_compra")
    _rename_if_exists("ALTER TABLE normalized_ordenes_compra_items RENAME TO silver_ordenes_compra_items")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_licitaciones_estado RENAME TO ix_silver_licitaciones_estado")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_licitaciones_fecha_publicacion RENAME TO ix_silver_licitaciones_fecha_publicacion")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_licitaciones_is_elegible_mvp RENAME TO ix_silver_licitaciones_is_elegible_mvp")
    _rename_if_exists(
        "ALTER INDEX IF EXISTS ix_normalized_licitaciones_tipo_adquisicion_norm "
        "RENAME TO ix_silver_licitaciones_tipo_adquisicion_norm"
    )
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_licitacion_items_codigo_externo RENAME TO ix_silver_licitacion_items_codigo_externo")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_licitacion_items_codigo_producto_onu RENAME TO ix_silver_licitacion_items_codigo_producto_onu")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ofertas_codigo_externo RENAME TO ix_silver_ofertas_codigo_externo")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ofertas_codigo_proveedor RENAME TO ix_silver_ofertas_codigo_proveedor")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ofertas_rut_proveedor RENAME TO ix_silver_ofertas_rut_proveedor")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ordenes_compra_estado RENAME TO ix_silver_ordenes_compra_estado")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ordenes_compra_fecha_envio RENAME TO ix_silver_ordenes_compra_fecha_envio")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ordenes_compra_codigo_licitacion RENAME TO ix_silver_ordenes_compra_codigo_licitacion")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ordenes_compra_codigo_proveedor RENAME TO ix_silver_ordenes_compra_codigo_proveedor")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ordenes_compra_codigo_unidad_compra RENAME TO ix_silver_ordenes_compra_codigo_unidad_compra")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ordenes_compra_items_codigo_oc RENAME TO ix_silver_ordenes_compra_items_codigo_oc")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_normalized_ordenes_compra_items_codigo_producto_onu RENAME TO ix_silver_ordenes_compra_items_codigo_producto_onu")
    _rename_if_exists("ALTER TABLE silver_licitacion_items RENAME CONSTRAINT uq_normalized_lic_item TO uq_silver_lic_item")
    _rename_if_exists("ALTER TABLE silver_ordenes_compra_items RENAME CONSTRAINT uq_normalized_oc_item TO uq_silver_oc_item")
    _rename_if_exists("ALTER TABLE raw_licitaciones RENAME TO bronze_licitaciones_raw")
    _rename_if_exists("ALTER TABLE raw_ordenes_compra RENAME TO bronze_ordenes_compra_raw")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_raw_licitaciones_codigo_externo RENAME TO ix_bronze_licitaciones_raw_codigo_externo")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_raw_ordenes_compra_codigo_oc RENAME TO ix_bronze_ordenes_compra_raw_codigo_oc")
    _rename_if_exists("ALTER INDEX IF EXISTS ix_raw_ordenes_compra_codigo_licitacion RENAME TO ix_bronze_ordenes_compra_raw_codigo_licitacion")
    _rename_if_exists("ALTER TABLE bronze_licitaciones_raw RENAME CONSTRAINT uq_raw_lic_raw_file_row TO uq_bronze_lic_raw_file_row")
    _rename_if_exists("ALTER TABLE bronze_ordenes_compra_raw RENAME CONSTRAINT uq_raw_oc_raw_file_row TO uq_bronze_oc_raw_file_row")
    _rename_if_exists("ALTER SEQUENCE IF EXISTS raw_licitaciones_id_seq RENAME TO bronze_licitaciones_raw_id_seq")
    _rename_if_exists("ALTER SEQUENCE IF EXISTS raw_ordenes_compra_id_seq RENAME TO bronze_ordenes_compra_raw_id_seq")
