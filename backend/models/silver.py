import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from backend.db.base import Base


class SilverLicitacion(Base):
    __tablename__ = "silver_licitaciones"

    codigo_externo = sa.Column(sa.Text, primary_key=True)
    codigo = sa.Column(sa.Text, nullable=False)

    nombre = sa.Column(sa.Text)
    descripcion = sa.Column(sa.Text)

    tipo_adquisicion = sa.Column(sa.Text)
    tipo_adquisicion_norm = sa.Column(sa.Text)

    codigo_estado = sa.Column(sa.Integer)
    estado = sa.Column(sa.Text)
    tipo = sa.Column(sa.Text)
    tipo_convocatoria = sa.Column(sa.Text)

    moneda_adquisicion = sa.Column(sa.Text)
    visibilidad_monto_raw = sa.Column(sa.Text)
    monto_estimado = sa.Column(sa.Numeric(20, 6))
    numero_oferentes = sa.Column(sa.Integer)

    codigo_organismo = sa.Column(sa.Text)
    nombre_organismo = sa.Column(sa.Text)
    codigo_unidad = sa.Column(sa.Text)
    nombre_unidad = sa.Column(sa.Text)
    comuna_unidad = sa.Column(sa.Text)
    region_unidad = sa.Column(sa.Text)

    fecha_publicacion = sa.Column(sa.DateTime)
    fecha_cierre = sa.Column(sa.DateTime)
    fecha_adjudicacion = sa.Column(sa.DateTime)
    fecha_estimada_adjudicacion = sa.Column(sa.DateTime)
    fecha_inicio = sa.Column(sa.DateTime)
    fecha_final = sa.Column(sa.DateTime)
    cantidad_dias_licitacion = sa.Column(sa.Integer)

    flag_licitacion_publica = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    flag_licitacion_privada = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    flag_licitacion_servicios = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    flag_menos_100_utm = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_elegible_mvp = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_licitaciones_estado", "estado"),
        sa.Index("ix_silver_licitaciones_fecha_publicacion", "fecha_publicacion"),
        sa.Index("ix_silver_licitaciones_is_elegible_mvp", "is_elegible_mvp"),
        sa.Index("ix_silver_licitaciones_tipo_adquisicion_norm", "tipo_adquisicion_norm"),
    )


class SilverLicitacionItem(Base):
    __tablename__ = "silver_licitacion_items"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    codigo_externo = sa.Column(
        sa.Text, sa.ForeignKey("silver_licitaciones.codigo_externo"), nullable=False
    )
    codigo_item = sa.Column(sa.Text, nullable=False)
    correlativo = sa.Column(sa.Text)

    codigo_producto_onu = sa.Column(sa.Text)
    nombre_producto_generico = sa.Column(sa.Text)
    nombre_linea_adquisicion = sa.Column(sa.Text)
    descripcion_linea_adquisicion = sa.Column(sa.Text)
    unidad_medida = sa.Column(sa.Text)
    cantidad = sa.Column(sa.Numeric(20, 6))
    rubro1 = sa.Column(sa.Text)
    rubro2 = sa.Column(sa.Text)
    rubro3 = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint("codigo_externo", "codigo_item", name="uq_silver_lic_item"),
        sa.Index("ix_silver_licitacion_items_codigo_externo", "codigo_externo"),
        sa.Index("ix_silver_licitacion_items_codigo_producto_onu", "codigo_producto_onu"),
    )


class SilverOferta(Base):
    __tablename__ = "silver_ofertas"

    oferta_key_sha256 = sa.Column(sa.String(64), primary_key=True)
    codigo_externo = sa.Column(
        sa.Text, sa.ForeignKey("silver_licitaciones.codigo_externo"), nullable=False
    )
    codigo_item = sa.Column(sa.Text)
    correlativo = sa.Column(sa.Text)

    codigo_proveedor = sa.Column(sa.Text)
    rut_proveedor = sa.Column(sa.Text)
    nombre_proveedor = sa.Column(sa.Text)
    razon_social_proveedor = sa.Column(sa.Text)

    estado_oferta = sa.Column(sa.Text)
    nombre_oferta = sa.Column(sa.Text)

    cantidad_ofertada = sa.Column(sa.Numeric(20, 6))
    monto_unitario_oferta = sa.Column(sa.Numeric(20, 6))
    valor_total_ofertado = sa.Column(sa.Numeric(20, 6))
    oferta_seleccionada = sa.Column(sa.Boolean)
    fecha_envio_oferta = sa.Column(sa.DateTime)

    cantidad_adjudicada = sa.Column(sa.Numeric(20, 6))
    monto_linea_adjudica = sa.Column(sa.Numeric(20, 6))
    monto_estimado_adjudicado = sa.Column(sa.Numeric(20, 6))

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_ofertas_codigo_externo", "codigo_externo"),
        sa.Index("ix_silver_ofertas_codigo_proveedor", "codigo_proveedor"),
        sa.Index("ix_silver_ofertas_rut_proveedor", "rut_proveedor"),
    )


class SilverOrdenCompra(Base):
    __tablename__ = "silver_ordenes_compra"

    codigo_oc = sa.Column(sa.Text, primary_key=True)
    id_oc_raw = sa.Column(sa.Text)

    link = sa.Column(sa.Text)
    nombre = sa.Column(sa.Text)
    descripcion_observaciones = sa.Column(sa.Text)

    tipo = sa.Column(sa.Text)
    procedencia_oc = sa.Column(sa.Text)
    es_trato_directo = sa.Column(sa.Boolean)
    es_compra_agil = sa.Column(sa.Boolean)
    codigo_tipo = sa.Column(sa.Text)
    codigo_abreviado_tipo_oc = sa.Column(sa.Text)
    descripcion_tipo_oc = sa.Column(sa.Text)

    codigo_estado = sa.Column(sa.Text)
    estado = sa.Column(sa.Text)
    codigo_estado_proveedor = sa.Column(sa.Text)
    estado_proveedor = sa.Column(sa.Text)

    fecha_creacion = sa.Column(sa.DateTime)
    fecha_envio = sa.Column(sa.DateTime)
    fecha_solicitud_cancelacion = sa.Column(sa.DateTime)
    fecha_aceptacion = sa.Column(sa.DateTime)
    fecha_cancelacion = sa.Column(sa.DateTime)
    fecha_ultima_modificacion = sa.Column(sa.DateTime)

    tiene_items = sa.Column(sa.Boolean)
    promedio_calificacion = sa.Column(sa.Numeric(20, 6))
    cantidad_evaluacion = sa.Column(sa.Integer)

    tipo_moneda_oc = sa.Column(sa.Text)
    monto_total_oc = sa.Column(sa.Numeric(20, 6))
    monto_total_oc_pesos_chilenos = sa.Column(sa.Numeric(20, 6))
    impuestos = sa.Column(sa.Numeric(20, 6))
    tipo_impuesto = sa.Column(sa.Text)
    descuentos = sa.Column(sa.Numeric(20, 6))
    cargos = sa.Column(sa.Numeric(20, 6))
    total_neto_oc = sa.Column(sa.Numeric(20, 6))
    total_cargos = sa.Column(sa.Numeric(20, 6))
    total_descuentos = sa.Column(sa.Numeric(20, 6))
    total_impuestos = sa.Column(sa.Numeric(20, 6))
    porcentaje_iva = sa.Column(sa.Numeric(20, 6))

    codigo_licitacion = sa.Column(sa.Text)
    codigo_convenio_marco = sa.Column(sa.Text)
    has_codigo_licitacion = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    codigo_unidad_compra = sa.Column(sa.Text)
    rut_unidad_compra = sa.Column(sa.Text)
    unidad_compra = sa.Column(sa.Text)
    codigo_organismo_publico = sa.Column(sa.Text)
    organismo_publico = sa.Column(sa.Text)
    sector = sa.Column(sa.Text)
    actividad_comprador = sa.Column(sa.Text)
    ciudad_unidad_compra = sa.Column(sa.Text)
    region_unidad_compra = sa.Column(sa.Text)
    pais_unidad_compra = sa.Column(sa.Text)

    codigo_sucursal = sa.Column(sa.Text)
    rut_sucursal = sa.Column(sa.Text)
    sucursal = sa.Column(sa.Text)
    codigo_proveedor = sa.Column(sa.Text)
    nombre_proveedor = sa.Column(sa.Text)
    actividad_proveedor = sa.Column(sa.Text)
    comuna_proveedor = sa.Column(sa.Text)
    region_proveedor = sa.Column(sa.Text)
    pais_proveedor = sa.Column(sa.Text)

    financiamiento = sa.Column(sa.Text)
    pais = sa.Column(sa.Text)
    tipo_despacho = sa.Column(sa.Text)
    forma_pago = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_ordenes_compra_estado", "estado"),
        sa.Index("ix_silver_ordenes_compra_fecha_envio", "fecha_envio"),
        sa.Index("ix_silver_ordenes_compra_codigo_licitacion", "codigo_licitacion"),
        sa.Index("ix_silver_ordenes_compra_codigo_proveedor", "codigo_proveedor"),
        sa.Index("ix_silver_ordenes_compra_codigo_unidad_compra", "codigo_unidad_compra"),
    )


class SilverOrdenCompraItem(Base):
    __tablename__ = "silver_ordenes_compra_items"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    codigo_oc = sa.Column(sa.Text, sa.ForeignKey("silver_ordenes_compra.codigo_oc"), nullable=False)
    id_item = sa.Column(sa.Text, nullable=False)

    codigo_producto_onu = sa.Column(sa.Text)
    codigo_categoria = sa.Column(sa.Text)
    categoria = sa.Column(sa.Text)
    nombre_producto_generico = sa.Column(sa.Text)
    rubro_n1 = sa.Column(sa.Text)
    rubro_n2 = sa.Column(sa.Text)
    rubro_n3 = sa.Column(sa.Text)
    especificacion_comprador = sa.Column(sa.Text)
    especificacion_proveedor = sa.Column(sa.Text)
    cantidad = sa.Column(sa.Numeric(20, 6))
    unidad_medida = sa.Column(sa.Text)
    moneda_item = sa.Column(sa.Text)
    precio_neto = sa.Column(sa.Numeric(20, 6))
    total_cargos = sa.Column(sa.Numeric(20, 6))
    total_descuentos = sa.Column(sa.Numeric(20, 6))
    total_impuestos = sa.Column(sa.Numeric(20, 6))
    total_linea_neto = sa.Column(sa.Numeric(20, 6))

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint("codigo_oc", "id_item", name="uq_silver_oc_item"),
        sa.Index("ix_silver_ordenes_compra_items_codigo_oc", "codigo_oc"),
        sa.Index("ix_silver_ordenes_compra_items_codigo_producto_onu", "codigo_producto_onu"),
    )
