import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from backend.db.base import Base


class NormalizedLicitacion(Base):
    __tablename__ = "normalized_licitaciones"

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
        sa.Index("ix_normalized_licitaciones_estado", "estado"),
        sa.Index("ix_normalized_licitaciones_fecha_publicacion", "fecha_publicacion"),
        sa.Index("ix_normalized_licitaciones_is_elegible_mvp", "is_elegible_mvp"),
        sa.Index("ix_normalized_licitaciones_tipo_adquisicion_norm", "tipo_adquisicion_norm"),
    )


class NormalizedLicitacionItem(Base):
    __tablename__ = "normalized_licitacion_items"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    codigo_externo = sa.Column(
        sa.Text, sa.ForeignKey("normalized_licitaciones.codigo_externo"), nullable=False
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
        sa.UniqueConstraint("codigo_externo", "codigo_item", name="uq_normalized_lic_item"),
        sa.Index("ix_normalized_licitacion_items_codigo_externo", "codigo_externo"),
        sa.Index("ix_normalized_licitacion_items_codigo_producto_onu", "codigo_producto_onu"),
    )


class NormalizedBuyer(Base):
    __tablename__ = "normalized_buyers"

    buyer_key = sa.Column(sa.Text, primary_key=True)
    codigo_unidad_compra = sa.Column(sa.Text, nullable=False)
    rut_unidad_compra = sa.Column(sa.Text)
    unidad_compra = sa.Column(sa.Text)
    codigo_organismo_publico = sa.Column(sa.Text)
    organismo_publico = sa.Column(sa.Text)
    sector = sa.Column(sa.Text)
    actividad_comprador = sa.Column(sa.Text)
    ciudad_unidad_compra = sa.Column(sa.Text)
    region_unidad_compra = sa.Column(sa.Text)
    pais_unidad_compra = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_normalized_buyers_codigo_unidad_compra", "codigo_unidad_compra"),
        sa.Index("ix_normalized_buyers_codigo_organismo_publico", "codigo_organismo_publico"),
    )


class NormalizedSupplier(Base):
    __tablename__ = "normalized_suppliers"

    supplier_key = sa.Column(sa.Text, primary_key=True)
    codigo_proveedor = sa.Column(sa.Text)
    rut_proveedor = sa.Column(sa.Text)
    nombre_proveedor = sa.Column(sa.Text)
    razon_social_proveedor = sa.Column(sa.Text)
    actividad_proveedor = sa.Column(sa.Text)
    comuna_proveedor = sa.Column(sa.Text)
    region_proveedor = sa.Column(sa.Text)
    pais_proveedor = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_normalized_suppliers_codigo_proveedor", "codigo_proveedor"),
        sa.Index("ix_normalized_suppliers_rut_proveedor", "rut_proveedor"),
    )


class NormalizedCategory(Base):
    __tablename__ = "normalized_categories"

    category_key = sa.Column(sa.Text, primary_key=True)
    codigo_categoria = sa.Column(sa.Text, nullable=False)
    categoria = sa.Column(sa.Text)
    rubro_n1 = sa.Column(sa.Text)
    rubro_n2 = sa.Column(sa.Text)
    rubro_n3 = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_normalized_categories_codigo_categoria", "codigo_categoria"),
    )


class NormalizedOferta(Base):
    __tablename__ = "normalized_ofertas"

    oferta_key_sha256 = sa.Column(sa.String(64), primary_key=True)
    codigo_externo = sa.Column(
        sa.Text, sa.ForeignKey("normalized_licitaciones.codigo_externo"), nullable=False
    )
    codigo_item = sa.Column(sa.Text)
    correlativo = sa.Column(sa.Text)

    codigo_proveedor = sa.Column(sa.Text)
    rut_proveedor = sa.Column(sa.Text)
    supplier_key = sa.Column(sa.Text, sa.ForeignKey("normalized_suppliers.supplier_key"))
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
        sa.Index("ix_normalized_ofertas_codigo_externo", "codigo_externo"),
        sa.Index("ix_normalized_ofertas_codigo_proveedor", "codigo_proveedor"),
        sa.Index("ix_normalized_ofertas_rut_proveedor", "rut_proveedor"),
        sa.Index("ix_normalized_ofertas_supplier_key", "supplier_key"),
    )


class NormalizedOrdenCompra(Base):
    __tablename__ = "normalized_ordenes_compra"

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
    buyer_key = sa.Column(sa.Text, sa.ForeignKey("normalized_buyers.buyer_key"))
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
    supplier_key = sa.Column(sa.Text, sa.ForeignKey("normalized_suppliers.supplier_key"))
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
        sa.Index("ix_normalized_ordenes_compra_estado", "estado"),
        sa.Index("ix_normalized_ordenes_compra_fecha_envio", "fecha_envio"),
        sa.Index("ix_normalized_ordenes_compra_codigo_licitacion", "codigo_licitacion"),
        sa.Index("ix_normalized_ordenes_compra_codigo_proveedor", "codigo_proveedor"),
        sa.Index("ix_normalized_ordenes_compra_codigo_unidad_compra", "codigo_unidad_compra"),
        sa.Index("ix_normalized_ordenes_compra_buyer_key", "buyer_key"),
        sa.Index("ix_normalized_ordenes_compra_supplier_key", "supplier_key"),
    )


class NormalizedOrdenCompraItem(Base):
    __tablename__ = "normalized_ordenes_compra_items"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    codigo_oc = sa.Column(sa.Text, sa.ForeignKey("normalized_ordenes_compra.codigo_oc"), nullable=False)
    id_item = sa.Column(sa.Text, nullable=False)

    codigo_producto_onu = sa.Column(sa.Text)
    codigo_categoria = sa.Column(sa.Text)
    category_key = sa.Column(sa.Text, sa.ForeignKey("normalized_categories.category_key"))
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
        sa.UniqueConstraint("codigo_oc", "id_item", name="uq_normalized_oc_item"),
        sa.Index("ix_normalized_ordenes_compra_items_codigo_oc", "codigo_oc"),
        sa.Index("ix_normalized_ordenes_compra_items_codigo_producto_onu", "codigo_producto_onu"),
        sa.Index("ix_normalized_ordenes_compra_items_category_key", "category_key"),
    )


class SilverNotice(Base):
    __tablename__ = "silver_notice"

    notice_id = sa.Column(sa.Text, primary_key=True)
    external_notice_code = sa.Column(sa.Text)
    notice_url = sa.Column(sa.Text)
    notice_title = sa.Column(sa.Text)
    notice_description_raw = sa.Column(sa.Text)
    notice_description_clean = sa.Column(sa.Text)
    procurement_method_name = sa.Column(sa.Text)
    procurement_method_code = sa.Column(sa.Text)
    notice_status_name = sa.Column(sa.Text)
    notice_status_code = sa.Column(sa.Text)

    publication_date = sa.Column(sa.DateTime)
    created_date = sa.Column(sa.DateTime)
    close_date = sa.Column(sa.DateTime)
    award_date = sa.Column(sa.DateTime)
    estimated_award_date = sa.Column(sa.DateTime)

    estimated_amount = sa.Column(sa.Numeric(20, 6))
    currency_code = sa.Column(sa.Text)
    currency_name = sa.Column(sa.Text)

    number_of_bidders_reported = sa.Column(sa.Integer)
    complaint_count = sa.Column(sa.Integer)
    days_publication_to_close = sa.Column(sa.Integer)
    days_creation_to_close = sa.Column(sa.Integer)
    days_close_to_award = sa.Column(sa.Integer)
    has_missing_date_chain_flag = sa.Column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    is_public_tender_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_private_tender_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    requires_toma_razon_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    multiple_stages_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    hidden_budget_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    has_extension_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    has_site_visit_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    has_physical_document_delivery_flag = sa.Column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    notice_line_count = sa.Column(sa.Integer)
    notice_bid_count = sa.Column(sa.Integer)
    notice_supplier_count = sa.Column(sa.Integer)
    notice_selected_bid_count = sa.Column(sa.Integer)
    notice_awarded_line_count = sa.Column(sa.Integer)

    notice_has_purchase_order_flag = sa.Column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    notice_purchase_order_count = sa.Column(sa.Integer)
    notice_awarded_to_order_conversion_flag = sa.Column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_notice_publication_date", "publication_date"),
        sa.Index("ix_silver_notice_status_name", "notice_status_name"),
    )


class SilverNoticeLine(Base):
    __tablename__ = "silver_notice_line"

    notice_line_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    notice_id = sa.Column(sa.Text, sa.ForeignKey("silver_notice.notice_id"), nullable=False)
    line_number = sa.Column(sa.Text)
    item_code = sa.Column(sa.Text, nullable=False)

    onu_product_code = sa.Column(sa.Text)
    category_level_1 = sa.Column(sa.Text)
    category_level_2 = sa.Column(sa.Text)
    category_level_3 = sa.Column(sa.Text)
    generic_product_name = sa.Column(sa.Text)
    line_name = sa.Column(sa.Text)
    line_description_raw = sa.Column(sa.Text)
    line_description_clean = sa.Column(sa.Text)
    unit_of_measure = sa.Column(sa.Text)
    quantity_requested = sa.Column(sa.Numeric(20, 6))

    line_bid_count = sa.Column(sa.Integer)
    line_supplier_count = sa.Column(sa.Integer)
    line_min_offer_amount = sa.Column(sa.Numeric(20, 6))
    line_max_offer_amount = sa.Column(sa.Numeric(20, 6))
    line_avg_offer_amount = sa.Column(sa.Numeric(20, 6))
    line_median_offer_amount = sa.Column(sa.Numeric(20, 6))
    line_price_dispersion_ratio = sa.Column(sa.Numeric(20, 6))

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint("notice_id", "item_code", name="uq_silver_notice_line_notice_item"),
        sa.Index("ix_silver_notice_line_notice_id", "notice_id"),
        sa.Index("ix_silver_notice_line_onu_product_code", "onu_product_code"),
    )


class SilverBidSubmission(Base):
    __tablename__ = "silver_bid_submission"

    bid_submission_id = sa.Column(sa.String(64), primary_key=True)
    notice_id = sa.Column(sa.Text, sa.ForeignKey("silver_notice.notice_id"), nullable=False)
    notice_line_id = sa.Column(sa.BigInteger, sa.ForeignKey("silver_notice_line.notice_line_id"))
    item_code = sa.Column(sa.Text)

    supplier_key = sa.Column(sa.Text)
    supplier_branch_id = sa.Column(sa.Text)

    offer_name = sa.Column(sa.Text)
    offer_status = sa.Column(sa.Text)
    offer_submission_date = sa.Column(sa.DateTime)
    offered_quantity = sa.Column(sa.Numeric(20, 6))
    offer_currency_name = sa.Column(sa.Text)
    unit_price_offered = sa.Column(sa.Numeric(20, 6))
    total_price_offered = sa.Column(sa.Numeric(20, 6))
    selected_offer_flag = sa.Column(sa.Boolean)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_bid_submission_notice_id", "notice_id"),
        sa.Index("ix_silver_bid_submission_supplier_key", "supplier_key"),
    )


class SilverAwardOutcome(Base):
    __tablename__ = "silver_award_outcome"

    award_outcome_id = sa.Column(sa.String(64), primary_key=True)
    bid_submission_id = sa.Column(sa.String(64), sa.ForeignKey("silver_bid_submission.bid_submission_id"))
    notice_id = sa.Column(sa.Text, sa.ForeignKey("silver_notice.notice_id"), nullable=False)
    notice_line_id = sa.Column(sa.BigInteger, sa.ForeignKey("silver_notice_line.notice_line_id"))
    item_code = sa.Column(sa.Text)

    supplier_key = sa.Column(sa.Text)
    selected_offer_flag = sa.Column(sa.Boolean)
    awarded_quantity = sa.Column(sa.Numeric(20, 6))
    awarded_line_amount = sa.Column(sa.Numeric(20, 6))
    award_date = sa.Column(sa.DateTime)
    award_status = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_award_outcome_notice_id", "notice_id"),
        sa.Index("ix_silver_award_outcome_supplier_key", "supplier_key"),
    )


class SilverPurchaseOrder(Base):
    __tablename__ = "silver_purchase_order"

    purchase_order_id = sa.Column(sa.Text, primary_key=True)
    purchase_order_code = sa.Column(sa.Text)
    purchase_order_url = sa.Column(sa.Text)
    purchase_order_name = sa.Column(sa.Text)
    purchase_order_description_raw = sa.Column(sa.Text)
    purchase_order_description_clean = sa.Column(sa.Text)

    purchase_order_type = sa.Column(sa.Text)
    purchase_order_type_code = sa.Column(sa.Text)
    purchase_order_status_code = sa.Column(sa.Text)
    purchase_order_status_name = sa.Column(sa.Text)
    supplier_status_code = sa.Column(sa.Text)
    supplier_status_name = sa.Column(sa.Text)

    order_created_at = sa.Column(sa.DateTime)
    order_sent_at = sa.Column(sa.DateTime)
    order_accepted_at = sa.Column(sa.DateTime)
    order_cancelled_at = sa.Column(sa.DateTime)
    order_last_modified_at = sa.Column(sa.DateTime)
    days_order_creation_to_acceptance = sa.Column(sa.Integer)
    days_order_creation_to_cancellation = sa.Column(sa.Integer)

    total_amount = sa.Column(sa.Numeric(20, 6))
    net_total_amount = sa.Column(sa.Numeric(20, 6))
    tax_amount = sa.Column(sa.Numeric(20, 6))
    discount_amount = sa.Column(sa.Numeric(20, 6))
    charge_amount = sa.Column(sa.Numeric(20, 6))
    currency_code = sa.Column(sa.Text)
    currency_name = sa.Column(sa.Text)

    supplier_key = sa.Column(sa.Text)
    supplier_branch_id = sa.Column(sa.Text)
    linked_notice_id = sa.Column(sa.Text)
    is_linked_to_notice_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_direct_award_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_agile_purchase_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    has_items_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    purchase_order_line_count = sa.Column(sa.Integer)
    purchase_order_total_quantity = sa.Column(sa.Numeric(20, 6))
    purchase_order_total_net_amount = sa.Column(sa.Numeric(20, 6))
    purchase_order_unique_product_count = sa.Column(sa.Integer)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_purchase_order_linked_notice_id", "linked_notice_id"),
        sa.Index("ix_silver_purchase_order_supplier_key", "supplier_key"),
        sa.Index("ix_silver_purchase_order_status_name", "purchase_order_status_name"),
    )


class SilverPurchaseOrderLine(Base):
    __tablename__ = "silver_purchase_order_line"

    purchase_order_line_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    purchase_order_id = sa.Column(
        sa.Text, sa.ForeignKey("silver_purchase_order.purchase_order_id"), nullable=False
    )
    line_item_id = sa.Column(sa.Text, nullable=False)
    linked_notice_id = sa.Column(sa.Text)

    onu_product_code = sa.Column(sa.Text)
    category_code = sa.Column(sa.Text)
    category_name = sa.Column(sa.Text)
    category_level_1 = sa.Column(sa.Text)
    category_level_2 = sa.Column(sa.Text)
    category_level_3 = sa.Column(sa.Text)
    generic_product_name = sa.Column(sa.Text)

    buyer_item_spec_raw = sa.Column(sa.Text)
    buyer_item_spec_clean = sa.Column(sa.Text)
    supplier_item_spec_raw = sa.Column(sa.Text)
    supplier_item_spec_clean = sa.Column(sa.Text)

    quantity_ordered = sa.Column(sa.Numeric(20, 6))
    unit_of_measure = sa.Column(sa.Text)
    line_currency = sa.Column(sa.Text)
    unit_net_price = sa.Column(sa.Numeric(20, 6))
    line_net_total = sa.Column(sa.Numeric(20, 6))
    line_tax_total = sa.Column(sa.Numeric(20, 6))
    line_discount_total = sa.Column(sa.Numeric(20, 6))
    line_charge_total = sa.Column(sa.Numeric(20, 6))

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)

    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint(
            "purchase_order_id", "line_item_id", name="uq_silver_purchase_order_line_order_item"
        ),
        sa.Index("ix_silver_purchase_order_line_order_id", "purchase_order_id"),
        sa.Index("ix_silver_purchase_order_line_linked_notice_id", "linked_notice_id"),
    )


class SilverBuyingOrg(Base):
    __tablename__ = "silver_buying_org"

    buying_org_id = sa.Column(sa.Text, primary_key=True)
    buying_org_name = sa.Column(sa.Text)
    sector_name = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_buying_org_name", "buying_org_name"),
    )


class SilverContractingUnit(Base):
    __tablename__ = "silver_contracting_unit"

    contracting_unit_id = sa.Column(sa.Text, primary_key=True)
    buying_org_id = sa.Column(sa.Text, sa.ForeignKey("silver_buying_org.buying_org_id"), nullable=False)
    unit_rut = sa.Column(sa.Text)
    unit_name = sa.Column(sa.Text)
    unit_address = sa.Column(sa.Text)
    unit_commune = sa.Column(sa.Text)
    unit_region = sa.Column(sa.Text)
    unit_city = sa.Column(sa.Text)
    unit_country = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_contracting_unit_buying_org_id", "buying_org_id"),
        sa.Index("ix_silver_contracting_unit_unit_rut", "unit_rut"),
    )


class SilverSupplier(Base):
    __tablename__ = "silver_supplier"

    supplier_id = sa.Column(sa.Text, primary_key=True)
    supplier_branch_id = sa.Column(sa.Text)
    supplier_rut = sa.Column(sa.Text)
    supplier_trade_name = sa.Column(sa.Text)
    supplier_legal_name = sa.Column(sa.Text)
    supplier_activity = sa.Column(sa.Text)
    supplier_commune = sa.Column(sa.Text)
    supplier_region = sa.Column(sa.Text)
    supplier_country = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_supplier_supplier_rut", "supplier_rut"),
        sa.Index("ix_silver_supplier_supplier_branch_id", "supplier_branch_id"),
    )


class SilverCategoryRef(Base):
    __tablename__ = "silver_category_ref"

    category_ref_id = sa.Column(sa.Text, primary_key=True)
    onu_product_code = sa.Column(sa.Text)
    category_code = sa.Column(sa.Text)
    category_name = sa.Column(sa.Text)
    category_level_1 = sa.Column(sa.Text)
    category_level_2 = sa.Column(sa.Text)
    category_level_3 = sa.Column(sa.Text)
    generic_product_name_canonical = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_category_ref_onu_product_code", "onu_product_code"),
        sa.Index("ix_silver_category_ref_category_code", "category_code"),
    )


class SilverNoticePurchaseOrderLink(Base):
    __tablename__ = "silver_notice_purchase_order_link"

    notice_purchase_order_link_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    notice_id = sa.Column(sa.Text, sa.ForeignKey("silver_notice.notice_id"), nullable=False)
    purchase_order_id = sa.Column(
        sa.Text, sa.ForeignKey("silver_purchase_order.purchase_order_id"), nullable=False
    )
    link_type = sa.Column(sa.Text, nullable=False)
    link_confidence = sa.Column(sa.Numeric(10, 6))
    source_system = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint(
            "notice_id",
            "purchase_order_id",
            "link_type",
            name="uq_silver_notice_purchase_order_link",
        ),
        sa.Index("ix_silver_notice_purchase_order_link_notice_id", "notice_id"),
        sa.Index("ix_silver_notice_purchase_order_link_purchase_order_id", "purchase_order_id"),
    )


class SilverSupplierParticipation(Base):
    __tablename__ = "silver_supplier_participation"

    supplier_participation_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    supplier_id = sa.Column(sa.Text, sa.ForeignKey("silver_supplier.supplier_id"), nullable=False)
    notice_id = sa.Column(sa.Text, sa.ForeignKey("silver_notice.notice_id"), nullable=False)
    notice_line_id = sa.Column(sa.BigInteger, sa.ForeignKey("silver_notice_line.notice_line_id"))
    bid_submission_id = sa.Column(sa.String(64), sa.ForeignKey("silver_bid_submission.bid_submission_id"))
    award_outcome_id = sa.Column(sa.String(64), sa.ForeignKey("silver_award_outcome.award_outcome_id"))
    purchase_order_line_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("silver_purchase_order_line.purchase_order_line_id")
    )

    was_selected_flag = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    was_materialized_in_purchase_order_flag = sa.Column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint(
            "supplier_id",
            "notice_id",
            name="uq_silver_supplier_participation_supplier_notice",
        ),
        sa.Index("ix_silver_supplier_participation_supplier_id", "supplier_id"),
        sa.Index("ix_silver_supplier_participation_notice_id", "notice_id"),
    )


class SilverNoticeTextAnn(Base):
    __tablename__ = "silver_notice_text_ann"

    notice_id = sa.Column(sa.Text, sa.ForeignKey("silver_notice.notice_id"), primary_key=True)
    nlp_version = sa.Column(sa.Text, primary_key=True)
    corpus_scope = sa.Column(sa.Text, nullable=False)
    language_detected = sa.Column(sa.Text)
    normalized_tokens_json = sa.Column(sa.JSON)
    top_ngrams_json = sa.Column(sa.JSON)
    keyword_flags_json = sa.Column(sa.JSON)
    domain_tags_json = sa.Column(sa.JSON)
    semantic_category_label = sa.Column(sa.Text)
    tfidf_artifact_ref = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.Index("ix_silver_notice_text_ann_semantic_category", "semantic_category_label"),
    )


class SilverNoticeLineTextAnn(Base):
    __tablename__ = "silver_notice_line_text_ann"

    notice_id = sa.Column(sa.Text, nullable=False, primary_key=True)
    item_code = sa.Column(sa.Text, nullable=False, primary_key=True)
    nlp_version = sa.Column(sa.Text, primary_key=True)
    corpus_scope = sa.Column(sa.Text, nullable=False)
    language_detected = sa.Column(sa.Text)
    normalized_tokens_json = sa.Column(sa.JSON)
    top_ngrams_json = sa.Column(sa.JSON)
    keyword_flags_json = sa.Column(sa.JSON)
    domain_tags_json = sa.Column(sa.JSON)
    semantic_category_label = sa.Column(sa.Text)
    tfidf_artifact_ref = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["notice_id"],
            ["silver_notice.notice_id"],
        ),
        sa.ForeignKeyConstraint(
            ["notice_id", "item_code"],
            ["silver_notice_line.notice_id", "silver_notice_line.item_code"],
        ),
        sa.Index("ix_silver_notice_line_text_ann_semantic_category", "semantic_category_label"),
    )


class SilverPurchaseOrderLineTextAnn(Base):
    __tablename__ = "silver_purchase_order_line_text_ann"

    purchase_order_id = sa.Column(sa.Text, nullable=False, primary_key=True)
    line_item_id = sa.Column(sa.Text, nullable=False, primary_key=True)
    nlp_version = sa.Column(sa.Text, primary_key=True)
    corpus_scope = sa.Column(sa.Text, nullable=False)
    language_detected = sa.Column(sa.Text)
    normalized_tokens_json = sa.Column(sa.JSON)
    top_ngrams_json = sa.Column(sa.JSON)
    buyer_spec_tags_json = sa.Column(sa.JSON)
    supplier_spec_tags_json = sa.Column(sa.JSON)
    semantic_category_label = sa.Column(sa.Text)
    tfidf_artifact_ref = sa.Column(sa.Text)

    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["purchase_order_id", "line_item_id"],
            ["silver_purchase_order_line.purchase_order_id", "silver_purchase_order_line.line_item_id"],
        ),
        sa.Index(
            "ix_silver_purchase_order_line_text_ann_semantic_category",
            "semantic_category_label",
        ),
    )
