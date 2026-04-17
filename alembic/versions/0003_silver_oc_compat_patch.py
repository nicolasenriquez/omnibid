"""silver oc compatibility patch for previously applied 0002

Revision ID: 0003_silver_oc_compat_patch
Revises: 0002_silver_v1_core
Create Date: 2026-04-16 22:10:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_silver_oc_compat_patch"
down_revision: Union[str, None] = "0002_silver_v1_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Header-level OC fields
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS id_oc_raw TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS fecha_solicitud_cancelacion TIMESTAMP")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS fecha_aceptacion TIMESTAMP")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS fecha_cancelacion TIMESTAMP")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS tiene_items BOOLEAN")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS promedio_calificacion NUMERIC(20,6)")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS cantidad_evaluacion INTEGER")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS descuentos NUMERIC(20,6)")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS cargos NUMERIC(20,6)")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS porcentaje_iva NUMERIC(20,6)")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS codigo_convenio_marco TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS codigo_unidad_compra TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS rut_unidad_compra TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS codigo_organismo_publico TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS organismo_publico TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS sector TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS actividad_comprador TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS ciudad_unidad_compra TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS region_unidad_compra TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS pais_unidad_compra TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS codigo_sucursal TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS rut_sucursal TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS sucursal TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS codigo_proveedor TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS actividad_proveedor TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS comuna_proveedor TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS region_proveedor TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS pais_proveedor TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS financiamiento TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS pais TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS tipo_despacho TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra ADD COLUMN IF NOT EXISTS forma_pago TEXT")

    # Item-level OC fields
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS codigo_categoria TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS categoria TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS nombre_producto_generico TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS rubro_n1 TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS rubro_n2 TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS rubro_n3 TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS especificacion_comprador TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS especificacion_proveedor TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS unidad_medida TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS moneda_item TEXT")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS precio_neto NUMERIC(20,6)")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS total_cargos NUMERIC(20,6)")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS total_descuentos NUMERIC(20,6)")
    op.execute("ALTER TABLE silver_ordenes_compra_items ADD COLUMN IF NOT EXISTS total_impuestos NUMERIC(20,6)")

    # Additional indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_silver_ordenes_compra_codigo_proveedor "
        "ON silver_ordenes_compra (codigo_proveedor)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_silver_ordenes_compra_codigo_unidad_compra "
        "ON silver_ordenes_compra (codigo_unidad_compra)"
    )


def downgrade() -> None:
    # Compatibility patch downgrade intentionally left as no-op.
    # We avoid destructive drops because this patch can run in mixed states.
    pass

