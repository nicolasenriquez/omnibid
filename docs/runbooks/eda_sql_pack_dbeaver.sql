-- EDA SQL Pack para DBeaver (PostgreSQL)
-- Contexto: ChileCompra middleman procurement analytics
-- Baseado en esquema repo: raw_*, normalized_*, silver_*, operational tables
-- Nota: prioriza silver_* para funnel; usa normalized_* para buyer analytics.

-- =====================================================================
-- A) DESCUBRIMIENTO DE ESQUEMA
-- =====================================================================

-- [A1] Tablas dominio y operational
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
  AND (
    table_name ~ '^(raw_|normalized_|silver_)'
    OR table_name IN (
      'source_files',
      'ingestion_batches',
      'pipeline_runs',
      'pipeline_run_steps',
      'data_quality_issues',
      'dataset_summary_snapshots'
    )
  )
ORDER BY table_name;

-- [A2] Columnas por tabla (tipo + nullability)
SELECT table_name, ordinal_position, column_name, data_type, udt_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
    table_name ~ '^(raw_|normalized_|silver_)'
    OR table_name IN ('source_files','ingestion_batches','pipeline_runs','pipeline_run_steps','data_quality_issues')
  )
ORDER BY table_name, ordinal_position;

-- [A3] PK / FK / UK
SELECT
  tc.table_name,
  tc.constraint_type,
  tc.constraint_name,
  kcu.column_name,
  ccu.table_name AS referenced_table,
  ccu.column_name AS referenced_column
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
 AND tc.table_name = kcu.table_name
LEFT JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name
 AND tc.table_schema = ccu.table_schema
WHERE tc.table_schema = 'public'
  AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE')
  AND (
    tc.table_name ~ '^(raw_|normalized_|silver_)'
    OR tc.table_name IN ('source_files','ingestion_batches','pipeline_runs','pipeline_run_steps','data_quality_issues')
  )
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name, kcu.ordinal_position;

-- [A4] Indices
SELECT tablename AS table_name, indexname AS index_name, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND (
    tablename ~ '^(raw_|normalized_|silver_)'
    OR tablename IN ('source_files','ingestion_batches','pipeline_runs','pipeline_run_steps','data_quality_issues')
  )
ORDER BY tablename, indexname;

-- [A5] Columnas texto candidatas para NLP
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND data_type IN ('text', 'character varying')
  AND table_name ~ '^(normalized_|silver_)'
ORDER BY table_name, column_name;

-- [A6] Columnas fecha/tiempo
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND data_type IN ('date', 'timestamp without time zone', 'timestamp with time zone')
  AND (
    table_name ~ '^(raw_|normalized_|silver_)'
    OR table_name IN ('source_files','ingestion_batches','pipeline_runs','pipeline_run_steps','data_quality_issues')
  )
ORDER BY table_name, column_name;

-- [A7] Columnas monetarias/cantidad
SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_schema = 'public'
  AND data_type IN ('numeric', 'integer', 'bigint', 'double precision', 'real')
  AND (
    column_name ILIKE '%monto%'
    OR column_name ILIKE '%amount%'
    OR column_name ILIKE '%price%'
    OR column_name ILIKE '%total%'
    OR column_name ILIKE '%cantidad%'
    OR column_name ILIKE '%quantity%'
    OR column_name ILIKE '%count%'
  )
ORDER BY table_name, column_name;

-- =====================================================================
-- B) COBERTURA Y VOLUMEN
-- =====================================================================

-- [B1] Volumen aproximado por tabla principal
SELECT relname AS table_name, n_live_tup::bigint AS approx_rows
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND (
    relname ~ '^(raw_|normalized_|silver_)'
    OR relname IN ('source_files','ingestion_batches','pipeline_runs','pipeline_run_steps','data_quality_issues')
  )
ORDER BY approx_rows DESC;

-- [B2] Distribucion temporal mensual (notices + OC + montos)
WITH notice_m AS (
  SELECT date_trunc('month', publication_date)::date AS month, count(*) AS notice_count
  FROM silver_notice
  WHERE publication_date IS NOT NULL
  GROUP BY 1
),
po_m AS (
  SELECT
    date_trunc('month', order_created_at)::date AS month,
    count(*) AS po_count,
    sum(total_amount) AS po_total_amount
  FROM silver_purchase_order
  WHERE order_created_at IS NOT NULL
  GROUP BY 1
)
SELECT
  COALESCE(n.month, p.month) AS month,
  COALESCE(n.notice_count, 0) AS notice_count,
  COALESCE(p.po_count, 0) AS po_count,
  COALESCE(p.po_total_amount, 0) AS po_total_amount
FROM notice_m n
FULL OUTER JOIN po_m p ON p.month = n.month
ORDER BY month;

-- [B3] Crecimiento/caida mensual
WITH base AS (
  SELECT
    date_trunc('month', order_created_at)::date AS month,
    count(*) AS po_count,
    sum(total_amount) AS po_total_amount
  FROM silver_purchase_order
  WHERE order_created_at IS NOT NULL
  GROUP BY 1
)
SELECT
  month,
  po_count,
  po_count - lag(po_count) OVER (ORDER BY month) AS po_count_delta,
  po_total_amount,
  po_total_amount - lag(po_total_amount) OVER (ORDER BY month) AS po_amount_delta
FROM base
ORDER BY month;

-- [B4] Estado notices vs OCs
SELECT 'notice' AS entity, COALESCE(notice_status_name, 'SIN_ESTADO') AS status, count(*) AS rows
FROM silver_notice
GROUP BY 1,2
UNION ALL
SELECT 'purchase_order' AS entity, COALESCE(purchase_order_status_name, 'SIN_ESTADO') AS status, count(*) AS rows
FROM silver_purchase_order
GROUP BY 1,2
ORDER BY entity, rows DESC;

-- [B5] Activas vs cerradas/canceladas (heuristica por nombre estado)
WITH states AS (
  SELECT
    purchase_order_status_name,
    CASE
      WHEN lower(COALESCE(purchase_order_status_name, '')) ~ '(cancel|anulad|rechaz)' THEN 'cancelled'
      WHEN lower(COALESCE(purchase_order_status_name, '')) ~ '(acept|cerrad|finaliz|complet)' THEN 'closed'
      ELSE 'active_or_other'
    END AS lifecycle_state
  FROM silver_purchase_order
)
SELECT lifecycle_state, count(*)
FROM states
GROUP BY lifecycle_state
ORDER BY count(*) DESC;

-- [B6] Frescura de datos por entidad core
SELECT 'silver_notice' AS table_name, max(publication_date) AS max_business_date, max(updated_at) AS max_load_date FROM silver_notice
UNION ALL
SELECT 'silver_bid_submission', max(offer_submission_date), max(updated_at) FROM silver_bid_submission
UNION ALL
SELECT 'silver_award_outcome', max(award_date), max(updated_at) FROM silver_award_outcome
UNION ALL
SELECT 'silver_purchase_order', max(order_created_at), max(updated_at) FROM silver_purchase_order
UNION ALL
SELECT 'silver_purchase_order_line', NULL::timestamp, max(updated_at) FROM silver_purchase_order_line
ORDER BY table_name;

-- =====================================================================
-- C) FUNNEL PROCUREMENT
-- =====================================================================

-- [C1] Cobertura funnel notice -> line -> bid -> award -> PO
WITH base AS (
  SELECT count(*)::numeric AS notices FROM silver_notice
),
line_cov AS (
  SELECT count(DISTINCT n.notice_id)::numeric AS notices_with_line
  FROM silver_notice n
  JOIN silver_notice_line nl ON nl.notice_id = n.notice_id
),
bid_cov AS (
  SELECT count(DISTINCT n.notice_id)::numeric AS notices_with_bid
  FROM silver_notice n
  JOIN silver_bid_submission b ON b.notice_id = n.notice_id
),
award_cov AS (
  SELECT count(DISTINCT n.notice_id)::numeric AS notices_with_award
  FROM silver_notice n
  JOIN silver_award_outcome a ON a.notice_id = n.notice_id
),
po_cov AS (
  SELECT count(DISTINCT n.notice_id)::numeric AS notices_with_po
  FROM silver_notice n
  LEFT JOIN silver_notice_purchase_order_link l ON l.notice_id = n.notice_id
  LEFT JOIN silver_purchase_order p ON p.linked_notice_id = n.notice_id
  WHERE l.notice_id IS NOT NULL OR p.purchase_order_id IS NOT NULL
)
SELECT
  b.notices,
  l.notices_with_line,
  round(100 * l.notices_with_line / NULLIF(b.notices, 0), 2) AS pct_notice_with_line,
  bd.notices_with_bid,
  round(100 * bd.notices_with_bid / NULLIF(b.notices, 0), 2) AS pct_notice_with_bid,
  a.notices_with_award,
  round(100 * a.notices_with_award / NULLIF(b.notices, 0), 2) AS pct_notice_with_award,
  p.notices_with_po,
  round(100 * p.notices_with_po / NULLIF(b.notices, 0), 2) AS pct_notice_with_po
FROM base b
CROSS JOIN line_cov l
CROSS JOIN bid_cov bd
CROSS JOIN award_cov a
CROSS JOIN po_cov p;

-- [C2] Promedios por notice: lineas, ofertas, suppliers
SELECT
  avg(COALESCE(notice_line_count, 0)) AS avg_lines_per_notice,
  avg(COALESCE(notice_bid_count, 0)) AS avg_bids_per_notice,
  avg(COALESCE(notice_supplier_count, 0)) AS avg_suppliers_per_notice
FROM silver_notice;

-- [C3] Conversion mensual notice -> award -> PO
WITH monthly AS (
  SELECT
    date_trunc('month', n.publication_date)::date AS month,
    count(DISTINCT n.notice_id) AS notices,
    count(DISTINCT a.notice_id) AS awarded_notices,
    count(DISTINCT CASE WHEN p.linked_notice_id IS NOT NULL OR l.notice_id IS NOT NULL THEN n.notice_id END) AS notices_with_po
  FROM silver_notice n
  LEFT JOIN silver_award_outcome a ON a.notice_id = n.notice_id
  LEFT JOIN silver_purchase_order p ON p.linked_notice_id = n.notice_id
  LEFT JOIN silver_notice_purchase_order_link l ON l.notice_id = n.notice_id
  WHERE n.publication_date IS NOT NULL
  GROUP BY 1
)
SELECT
  month,
  notices,
  awarded_notices,
  round(100 * awarded_notices::numeric / NULLIF(notices, 0), 2) AS pct_notice_to_award,
  notices_with_po,
  round(100 * notices_with_po::numeric / NULLIF(notices, 0), 2) AS pct_notice_to_po
FROM monthly
ORDER BY month;

-- [C4] OC enlazadas a notice (direct link field + bridge)
SELECT
  count(*) AS po_total,
  count(*) FILTER (WHERE linked_notice_id IS NOT NULL) AS po_with_linked_notice_id,
  round(100.0 * count(*) FILTER (WHERE linked_notice_id IS NOT NULL) / NULLIF(count(*),0), 2) AS pct_with_linked_notice_id,
  count(DISTINCT l.purchase_order_id) AS po_in_bridge,
  round(100.0 * count(DISTINCT l.purchase_order_id) / NULLIF(count(*),0), 2) AS pct_in_bridge
FROM silver_purchase_order p
LEFT JOIN silver_notice_purchase_order_link l
  ON l.purchase_order_id = p.purchase_order_id;

-- [C5] OC por notice + monto total OC por notice
SELECT
  notice_id,
  count(DISTINCT purchase_order_id) AS po_count,
  sum(total_amount) AS po_total_amount
FROM (
  SELECT linked_notice_id AS notice_id, purchase_order_id, total_amount
  FROM silver_purchase_order
  WHERE linked_notice_id IS NOT NULL
  UNION ALL
  SELECT l.notice_id, p.purchase_order_id, p.total_amount
  FROM silver_notice_purchase_order_link l
  JOIN silver_purchase_order p ON p.purchase_order_id = l.purchase_order_id
) x
GROUP BY notice_id
ORDER BY po_total_amount DESC NULLS LAST;

-- =====================================================================
-- D) BUYERS / COMPRADORES (ruta normalized_*)
-- =====================================================================

-- [D1] Top buyers por cantidad de licitaciones
SELECT
  COALESCE(codigo_unidad, 'SIN_UNIDAD') AS buyer_unit_code,
  COALESCE(nombre_unidad, 'SIN_NOMBRE_UNIDAD') AS buyer_unit_name,
  count(*) AS notice_count
FROM normalized_licitaciones
GROUP BY 1,2
ORDER BY notice_count DESC
LIMIT 50;

-- [D2] Top buyers por monto y cantidad de OC
SELECT
  COALESCE(o.codigo_unidad_compra, 'SIN_UNIDAD') AS buyer_unit_code,
  COALESCE(o.unidad_compra, 'SIN_NOMBRE_UNIDAD') AS buyer_unit_name,
  count(*) AS po_count,
  sum(o.monto_total_oc) AS po_total_amount
FROM normalized_ordenes_compra o
GROUP BY 1,2
ORDER BY po_total_amount DESC NULLS LAST
LIMIT 50;

-- [D3] Buyers por region/sector/unidad
SELECT
  COALESCE(region_unidad_compra, 'SIN_REGION') AS region,
  COALESCE(sector, 'SIN_SECTOR') AS sector,
  count(DISTINCT codigo_unidad_compra) AS buyers,
  count(*) AS po_count,
  sum(monto_total_oc) AS po_total_amount
FROM normalized_ordenes_compra
GROUP BY 1,2
ORDER BY po_total_amount DESC NULLS LAST;

-- [D4] Buyers con mayor trato directo
SELECT
  COALESCE(codigo_unidad_compra, 'SIN_UNIDAD') AS buyer_unit_code,
  COALESCE(unidad_compra, 'SIN_NOMBRE_UNIDAD') AS buyer_unit_name,
  count(*) AS po_total,
  count(*) FILTER (WHERE es_trato_directo IS TRUE) AS po_direct_award,
  round(100.0 * count(*) FILTER (WHERE es_trato_directo IS TRUE) / NULLIF(count(*),0), 2) AS pct_direct_award
FROM normalized_ordenes_compra
GROUP BY 1,2
HAVING count(*) >= 20
ORDER BY pct_direct_award DESC, po_total DESC;

-- [D5] Buyers mas concentrados en pocos proveedores (HHI)
WITH buyer_supplier AS (
  SELECT
    COALESCE(codigo_unidad_compra, 'SIN_UNIDAD') AS buyer_unit_code,
    COALESCE(supplier_key, 'SIN_SUPPLIER') AS supplier_key,
    count(*)::numeric AS po_count
  FROM normalized_ordenes_compra
  GROUP BY 1,2
),
shares AS (
  SELECT
    buyer_unit_code,
    supplier_key,
    po_count,
    po_count / sum(po_count) OVER (PARTITION BY buyer_unit_code) AS share
  FROM buyer_supplier
)
SELECT
  buyer_unit_code,
  count(*) AS supplier_count,
  round(sum(power(share, 2))::numeric, 4) AS hhi
FROM shares
GROUP BY buyer_unit_code
HAVING sum(po_count) > 0
ORDER BY hhi DESC, supplier_count ASC
LIMIT 100;

-- [D6] Buyers con mayor conversion licitacion -> OC
WITH notices AS (
  SELECT codigo_unidad AS buyer_unit_code, count(DISTINCT codigo_externo) AS notice_count
  FROM normalized_licitaciones
  GROUP BY 1
),
notice_po AS (
  SELECT l.codigo_unidad AS buyer_unit_code, count(DISTINCT l.codigo_externo) AS notice_with_po_count
  FROM normalized_licitaciones l
  JOIN normalized_ordenes_compra o
    ON o.codigo_licitacion = l.codigo_externo
  GROUP BY 1
)
SELECT
  n.buyer_unit_code,
  n.notice_count,
  COALESCE(p.notice_with_po_count, 0) AS notice_with_po_count,
  round(100.0 * COALESCE(p.notice_with_po_count,0) / NULLIF(n.notice_count,0), 2) AS notice_to_po_conversion_pct
FROM notices n
LEFT JOIN notice_po p ON p.buyer_unit_code = n.buyer_unit_code
WHERE n.notice_count >= 20
ORDER BY notice_to_po_conversion_pct DESC, n.notice_count DESC;

-- =====================================================================
-- E) SUPPLIERS / PROVEEDORES
-- =====================================================================

-- [E1] Top proveedores por participacion en ofertas
SELECT
  COALESCE(b.supplier_key, 'SIN_SUPPLIER') AS supplier_key,
  count(*) AS bid_count,
  count(DISTINCT b.notice_id) AS notice_count
FROM silver_bid_submission b
GROUP BY 1
ORDER BY bid_count DESC
LIMIT 100;

-- [E2] Top proveedores por OC y monto
SELECT
  COALESCE(p.supplier_key, 'SIN_SUPPLIER') AS supplier_key,
  count(*) AS po_count,
  sum(p.total_amount) AS po_total_amount
FROM silver_purchase_order p
GROUP BY 1
ORDER BY po_total_amount DESC NULLS LAST
LIMIT 100;

-- [E3] Proveedor por categoria principal (OC lines)
WITH supplier_category AS (
  SELECT
    COALESCE(p.supplier_key, 'SIN_SUPPLIER') AS supplier_key,
    COALESCE(l.category_code, l.category_level_3, l.category_level_2, l.category_level_1, 'SIN_CATEGORIA') AS category,
    count(*) AS line_count,
    sum(l.line_net_total) AS amount
  FROM silver_purchase_order p
  JOIN silver_purchase_order_line l ON l.purchase_order_id = p.purchase_order_id
  GROUP BY 1,2
),
ranked AS (
  SELECT *, row_number() OVER (PARTITION BY supplier_key ORDER BY amount DESC NULLS LAST, line_count DESC) AS rn
  FROM supplier_category
)
SELECT supplier_key, category AS main_category, line_count, amount
FROM ranked
WHERE rn = 1
ORDER BY amount DESC NULLS LAST
LIMIT 100;

-- [E4] Proveedor por buyer principal (normalized)
WITH supplier_buyer AS (
  SELECT
    COALESCE(supplier_key, 'SIN_SUPPLIER') AS supplier_key,
    COALESCE(codigo_unidad_compra, 'SIN_BUYER') AS buyer_unit_code,
    count(*) AS po_count,
    sum(monto_total_oc) AS amount
  FROM normalized_ordenes_compra
  GROUP BY 1,2
),
ranked AS (
  SELECT *, row_number() OVER (PARTITION BY supplier_key ORDER BY amount DESC NULLS LAST, po_count DESC) AS rn
  FROM supplier_buyer
)
SELECT supplier_key, buyer_unit_code AS main_buyer, po_count, amount
FROM ranked
WHERE rn = 1
ORDER BY amount DESC NULLS LAST
LIMIT 100;

-- [E5] Conversion proveedor oferta -> adjudicacion
SELECT
  supplier_id,
  count(DISTINCT notice_id) AS notices_participated,
  count(DISTINCT notice_id) FILTER (WHERE was_selected_flag IS TRUE) AS notices_selected,
  round(
    100.0 * count(DISTINCT notice_id) FILTER (WHERE was_selected_flag IS TRUE)
    / NULLIF(count(DISTINCT notice_id), 0),
    2
  ) AS offer_to_award_conversion_pct
FROM silver_supplier_participation
GROUP BY supplier_id
HAVING count(DISTINCT notice_id) >= 10
ORDER BY offer_to_award_conversion_pct DESC, notices_participated DESC
LIMIT 100;

-- [E6] Conversion proveedor adjudicacion -> OC
SELECT
  supplier_id,
  count(DISTINCT notice_id) FILTER (WHERE was_selected_flag IS TRUE) AS awarded_notices,
  count(DISTINCT notice_id) FILTER (WHERE was_materialized_in_purchase_order_flag IS TRUE) AS awarded_materialized,
  round(
    100.0 * count(DISTINCT notice_id) FILTER (WHERE was_materialized_in_purchase_order_flag IS TRUE)
    / NULLIF(count(DISTINCT notice_id) FILTER (WHERE was_selected_flag IS TRUE), 0),
    2
  ) AS award_to_po_conversion_pct
FROM silver_supplier_participation
GROUP BY supplier_id
HAVING count(DISTINCT notice_id) FILTER (WHERE was_selected_flag IS TRUE) >= 5
ORDER BY award_to_po_conversion_pct DESC, awarded_notices DESC
LIMIT 100;

-- =====================================================================
-- F) CATEGORIAS / RUBROS
-- =====================================================================

-- [F1] Top categorias por cantidad de licitaciones
SELECT
  COALESCE(category_level_3, category_level_2, category_level_1, 'SIN_CATEGORIA') AS category,
  count(DISTINCT notice_id) AS notice_count
FROM silver_notice_line
GROUP BY 1
ORDER BY notice_count DESC
LIMIT 50;

-- [F2] Top categorias por monto OC
SELECT
  COALESCE(category_code, category_level_3, category_level_2, category_level_1, 'SIN_CATEGORIA') AS category,
  sum(line_net_total) AS total_net_amount
FROM silver_purchase_order_line
GROUP BY 1
ORDER BY total_net_amount DESC NULLS LAST
LIMIT 50;

-- [F3] Top categorias por cantidad de OC lineas
SELECT
  COALESCE(category_code, category_level_3, category_level_2, category_level_1, 'SIN_CATEGORIA') AS category,
  count(*) AS po_line_count,
  count(DISTINCT purchase_order_id) AS po_count
FROM silver_purchase_order_line
GROUP BY 1
ORDER BY po_line_count DESC
LIMIT 50;

-- [F4] Categorias con mayor competencia (suppliers por notice)
WITH category_notice_supplier AS (
  SELECT
    COALESCE(nl.category_level_3, nl.category_level_2, nl.category_level_1, 'SIN_CATEGORIA') AS category,
    nl.notice_id,
    count(DISTINCT b.supplier_key) AS suppliers_per_notice
  FROM silver_notice_line nl
  LEFT JOIN silver_bid_submission b
    ON b.notice_id = nl.notice_id
   AND (b.item_code = nl.item_code OR b.notice_line_id = nl.notice_line_id)
  GROUP BY 1,2
)
SELECT
  category,
  avg(suppliers_per_notice)::numeric(10,2) AS avg_suppliers_per_notice,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY suppliers_per_notice) AS median_suppliers_per_notice
FROM category_notice_supplier
GROUP BY category
ORDER BY avg_suppliers_per_notice DESC
LIMIT 50;

-- [F5] Categorias con mas proveedores unicos (materializados en OC)
SELECT
  COALESCE(l.category_code, l.category_level_3, l.category_level_2, l.category_level_1, 'SIN_CATEGORIA') AS category,
  count(DISTINCT p.supplier_key) AS unique_suppliers
FROM silver_purchase_order_line l
JOIN silver_purchase_order p ON p.purchase_order_id = l.purchase_order_id
GROUP BY 1
ORDER BY unique_suppliers DESC
LIMIT 50;

-- [F6] Categorias con mas trato directo
SELECT
  COALESCE(l.category_code, l.category_level_3, l.category_level_2, l.category_level_1, 'SIN_CATEGORIA') AS category,
  count(*) AS total_lines,
  count(*) FILTER (WHERE p.is_direct_award_flag IS TRUE) AS direct_award_lines,
  round(
    100.0 * count(*) FILTER (WHERE p.is_direct_award_flag IS TRUE) / NULLIF(count(*),0),
    2
  ) AS pct_direct_award
FROM silver_purchase_order_line l
JOIN silver_purchase_order p ON p.purchase_order_id = l.purchase_order_id
GROUP BY 1
HAVING count(*) >= 30
ORDER BY pct_direct_award DESC, total_lines DESC;

-- [F7] Categorias mas frecuentes por buyer
SELECT
  COALESCE(o.codigo_unidad_compra, 'SIN_BUYER') AS buyer_unit_code,
  COALESCE(i.codigo_categoria, i.rubro_n3, i.rubro_n2, i.rubro_n1, 'SIN_CATEGORIA') AS category,
  count(*) AS line_count,
  sum(i.total_linea_neto) AS net_amount
FROM normalized_ordenes_compra o
JOIN normalized_ordenes_compra_items i ON i.codigo_oc = o.codigo_oc
GROUP BY 1,2
ORDER BY line_count DESC
LIMIT 200;

-- [F8] Categorias mas frecuentes por supplier
SELECT
  COALESCE(o.supplier_key, 'SIN_SUPPLIER') AS supplier_key,
  COALESCE(i.codigo_categoria, i.rubro_n3, i.rubro_n2, i.rubro_n1, 'SIN_CATEGORIA') AS category,
  count(*) AS line_count,
  sum(i.total_linea_neto) AS net_amount
FROM normalized_ordenes_compra o
JOIN normalized_ordenes_compra_items i ON i.codigo_oc = o.codigo_oc
GROUP BY 1,2
ORDER BY line_count DESC
LIMIT 200;

-- =====================================================================
-- G) COMPETENCIA
-- =====================================================================

-- [G1] Promedio oferentes por licitacion y por linea
WITH per_notice AS (
  SELECT notice_id, count(DISTINCT supplier_key) AS suppliers_per_notice
  FROM silver_bid_submission
  GROUP BY notice_id
),
per_line AS (
  SELECT notice_id, COALESCE(item_code, 'SIN_ITEM') AS item_code, count(DISTINCT supplier_key) AS suppliers_per_line
  FROM silver_bid_submission
  GROUP BY 1,2
)
SELECT
  (SELECT avg(suppliers_per_notice)::numeric(10,2) FROM per_notice) AS avg_suppliers_per_notice,
  (SELECT avg(suppliers_per_line)::numeric(10,2) FROM per_line) AS avg_suppliers_per_line;

-- [G2] Proveedores unicos por categoria
SELECT
  COALESCE(l.category_code, l.category_level_3, l.category_level_2, l.category_level_1, 'SIN_CATEGORIA') AS category,
  count(DISTINCT p.supplier_key) AS unique_suppliers
FROM silver_purchase_order_line l
JOIN silver_purchase_order p ON p.purchase_order_id = l.purchase_order_id
GROUP BY 1
ORDER BY unique_suppliers DESC;

-- [G3] Concentracion buyer-category por supplier (HHI)
WITH buyer_cat_supplier AS (
  SELECT
    COALESCE(o.codigo_unidad_compra, 'SIN_BUYER') AS buyer_unit_code,
    COALESCE(i.codigo_categoria, i.rubro_n3, i.rubro_n2, i.rubro_n1, 'SIN_CATEGORIA') AS category,
    COALESCE(o.supplier_key, 'SIN_SUPPLIER') AS supplier_key,
    count(*)::numeric AS lines
  FROM normalized_ordenes_compra o
  JOIN normalized_ordenes_compra_items i ON i.codigo_oc = o.codigo_oc
  GROUP BY 1,2,3
),
shares AS (
  SELECT
    buyer_unit_code,
    category,
    supplier_key,
    lines,
    lines / sum(lines) OVER (PARTITION BY buyer_unit_code, category) AS share
  FROM buyer_cat_supplier
)
SELECT
  buyer_unit_code,
  category,
  count(*) AS supplier_count,
  round(sum(power(share, 2))::numeric, 4) AS hhi
FROM shares
GROUP BY 1,2
HAVING sum(lines) >= 20
ORDER BY hhi DESC
LIMIT 200;

-- [G4] Dispersion de precios ofertados por linea
SELECT
  notice_id,
  COALESCE(item_code, 'SIN_ITEM') AS item_code,
  count(*) AS offer_count,
  min(unit_price_offered) AS min_price,
  max(unit_price_offered) AS max_price,
  avg(unit_price_offered) AS avg_price,
  stddev_pop(unit_price_offered) AS std_price,
  CASE WHEN avg(unit_price_offered) > 0 THEN stddev_pop(unit_price_offered) / avg(unit_price_offered) END AS cv_price
FROM silver_bid_submission
WHERE unit_price_offered IS NOT NULL
GROUP BY 1,2
HAVING count(*) >= 3
ORDER BY cv_price DESC NULLS LAST
LIMIT 200;

-- [G5] Segmentos alta vs baja competencia por categoria
WITH cat_comp AS (
  SELECT
    COALESCE(nl.category_level_3, nl.category_level_2, nl.category_level_1, 'SIN_CATEGORIA') AS category,
    nl.notice_id,
    count(DISTINCT b.supplier_key) AS suppliers_per_notice
  FROM silver_notice_line nl
  LEFT JOIN silver_bid_submission b
    ON b.notice_id = nl.notice_id
   AND (b.item_code = nl.item_code OR b.notice_line_id = nl.notice_line_id)
  GROUP BY 1,2
),
agg AS (
  SELECT
    category,
    avg(suppliers_per_notice)::numeric(10,2) AS avg_suppliers_per_notice
  FROM cat_comp
  GROUP BY 1
)
SELECT
  category,
  avg_suppliers_per_notice,
  CASE
    WHEN avg_suppliers_per_notice >= 5 THEN 'alta_competencia'
    WHEN avg_suppliers_per_notice >= 2 THEN 'media_competencia'
    ELSE 'baja_competencia'
  END AS competition_segment
FROM agg
ORDER BY avg_suppliers_per_notice DESC;

-- =====================================================================
-- H) TIEMPOS DE CICLO
-- =====================================================================

-- [H1] Dias publicacion -> cierre
SELECT
  avg(days_publication_to_close)::numeric(10,2) AS avg_days,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY days_publication_to_close) AS p50,
  percentile_cont(0.9) WITHIN GROUP (ORDER BY days_publication_to_close) AS p90
FROM silver_notice
WHERE days_publication_to_close IS NOT NULL;

-- [H2] Dias cierre -> adjudicacion
SELECT
  avg(days_close_to_award)::numeric(10,2) AS avg_days,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY days_close_to_award) AS p50,
  percentile_cont(0.9) WITHIN GROUP (ORDER BY days_close_to_award) AS p90
FROM silver_notice
WHERE days_close_to_award IS NOT NULL;

-- [H3] Dias creacion OC -> aceptacion
SELECT
  avg(days_order_creation_to_acceptance)::numeric(10,2) AS avg_days,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY days_order_creation_to_acceptance) AS p50,
  percentile_cont(0.9) WITHIN GROUP (ORDER BY days_order_creation_to_acceptance) AS p90
FROM silver_purchase_order
WHERE days_order_creation_to_acceptance IS NOT NULL;

-- [H4] Tiempos promedio por buyer (normalized OC)
SELECT
  COALESCE(codigo_unidad_compra, 'SIN_BUYER') AS buyer_unit_code,
  avg(fecha_aceptacion::date - fecha_creacion::date)::numeric(10,2) AS avg_days_creation_to_acceptance,
  avg(fecha_envio::date - fecha_creacion::date)::numeric(10,2) AS avg_days_creation_to_sent,
  count(*) AS po_count
FROM normalized_ordenes_compra
WHERE fecha_creacion IS NOT NULL
GROUP BY 1
HAVING count(*) >= 20
ORDER BY avg_days_creation_to_acceptance DESC NULLS LAST;

-- [H5] Tiempos promedio por categoria
SELECT
  COALESCE(l.category_code, l.category_level_3, l.category_level_2, l.category_level_1, 'SIN_CATEGORIA') AS category,
  avg(p.days_order_creation_to_acceptance)::numeric(10,2) AS avg_days_creation_to_acceptance,
  count(*) AS po_line_count
FROM silver_purchase_order_line l
JOIN silver_purchase_order p ON p.purchase_order_id = l.purchase_order_id
WHERE p.days_order_creation_to_acceptance IS NOT NULL
GROUP BY 1
HAVING count(*) >= 30
ORDER BY avg_days_creation_to_acceptance DESC;

-- [H6] Licitaciones con plazos unusually short
SELECT
  notice_id,
  notice_title,
  publication_date,
  close_date,
  days_publication_to_close
FROM silver_notice
WHERE days_publication_to_close IS NOT NULL
  AND days_publication_to_close <= 2
ORDER BY days_publication_to_close ASC, publication_date DESC;

-- [H7] OC demoradas en aceptacion
SELECT
  purchase_order_id,
  purchase_order_name,
  order_created_at,
  order_accepted_at,
  days_order_creation_to_acceptance,
  total_amount,
  supplier_key
FROM silver_purchase_order
WHERE days_order_creation_to_acceptance IS NOT NULL
  AND days_order_creation_to_acceptance >= 30
ORDER BY days_order_creation_to_acceptance DESC;

-- [H8] Percentiles completos de ciclo OC
SELECT
  percentile_cont(0.1) WITHIN GROUP (ORDER BY days_order_creation_to_acceptance) AS p10,
  percentile_cont(0.25) WITHIN GROUP (ORDER BY days_order_creation_to_acceptance) AS p25,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY days_order_creation_to_acceptance) AS p50,
  percentile_cont(0.75) WITHIN GROUP (ORDER BY days_order_creation_to_acceptance) AS p75,
  percentile_cont(0.9) WITHIN GROUP (ORDER BY days_order_creation_to_acceptance) AS p90
FROM silver_purchase_order
WHERE days_order_creation_to_acceptance IS NOT NULL;

-- =====================================================================
-- I) RELACION LICITACION <-> ORDEN DE COMPRA
-- =====================================================================

-- [I1] % OC con linked_notice_id
SELECT
  count(*) AS po_total,
  count(*) FILTER (WHERE linked_notice_id IS NOT NULL) AS po_with_linked_notice,
  round(100.0 * count(*) FILTER (WHERE linked_notice_id IS NOT NULL) / NULLIF(count(*),0), 2) AS pct_po_with_linked_notice
FROM silver_purchase_order;

-- [I2] % notices que terminan en OC
WITH n AS (
  SELECT count(*)::numeric AS total_notices FROM silver_notice
),
np AS (
  SELECT count(DISTINCT notice_id)::numeric AS notices_with_po
  FROM (
    SELECT linked_notice_id AS notice_id FROM silver_purchase_order WHERE linked_notice_id IS NOT NULL
    UNION
    SELECT notice_id FROM silver_notice_purchase_order_link
  ) x
)
SELECT
  n.total_notices,
  np.notices_with_po,
  round(100 * np.notices_with_po / NULLIF(n.total_notices, 0), 2) AS pct_notice_with_po
FROM n, np;

-- [I3] Cuantas OC por notice + monto
SELECT
  notice_id,
  count(DISTINCT purchase_order_id) AS po_count,
  sum(total_amount) AS po_total_amount,
  avg(total_amount) AS po_avg_amount
FROM (
  SELECT linked_notice_id AS notice_id, purchase_order_id, total_amount
  FROM silver_purchase_order
  WHERE linked_notice_id IS NOT NULL
  UNION ALL
  SELECT l.notice_id, p.purchase_order_id, p.total_amount
  FROM silver_notice_purchase_order_link l
  JOIN silver_purchase_order p ON p.purchase_order_id = l.purchase_order_id
) x
GROUP BY notice_id
ORDER BY po_total_amount DESC NULLS LAST;

-- [I4] Buyers con mejor conversion notice -> OC (normalized)
WITH notice_by_buyer AS (
  SELECT codigo_unidad AS buyer_unit_code, count(DISTINCT codigo_externo) AS notices
  FROM normalized_licitaciones
  GROUP BY 1
),
notice_po_by_buyer AS (
  SELECT l.codigo_unidad AS buyer_unit_code, count(DISTINCT l.codigo_externo) AS notices_with_po
  FROM normalized_licitaciones l
  JOIN normalized_ordenes_compra o ON o.codigo_licitacion = l.codigo_externo
  GROUP BY 1
)
SELECT
  n.buyer_unit_code,
  n.notices,
  COALESCE(p.notices_with_po, 0) AS notices_with_po,
  round(100.0 * COALESCE(p.notices_with_po,0) / NULLIF(n.notices,0), 2) AS conversion_pct
FROM notice_by_buyer n
LEFT JOIN notice_po_by_buyer p ON p.buyer_unit_code = n.buyer_unit_code
WHERE n.notices >= 20
ORDER BY conversion_pct DESC, n.notices DESC;

-- [I5] Suppliers con mejor conversion notice -> OC
SELECT
  supplier_id,
  count(DISTINCT notice_id) AS notices_participated,
  count(DISTINCT notice_id) FILTER (WHERE was_materialized_in_purchase_order_flag IS TRUE) AS notices_materialized,
  round(
    100.0 * count(DISTINCT notice_id) FILTER (WHERE was_materialized_in_purchase_order_flag IS TRUE)
    / NULLIF(count(DISTINCT notice_id), 0),
    2
  ) AS conversion_pct
FROM silver_supplier_participation
GROUP BY supplier_id
HAVING count(DISTINCT notice_id) >= 10
ORDER BY conversion_pct DESC, notices_participated DESC;

-- [I6] Categorias con mejor conversion notice -> OC
WITH notice_cat AS (
  SELECT DISTINCT
    nl.notice_id,
    COALESCE(nl.category_level_3, nl.category_level_2, nl.category_level_1, 'SIN_CATEGORIA') AS category
  FROM silver_notice_line nl
),
po_cat AS (
  SELECT DISTINCT
    linked_notice_id AS notice_id,
    COALESCE(category_code, category_level_3, category_level_2, category_level_1, 'SIN_CATEGORIA') AS category
  FROM silver_purchase_order_line
  WHERE linked_notice_id IS NOT NULL
)
SELECT
  nc.category,
  count(DISTINCT nc.notice_id) AS notices,
  count(DISTINCT pc.notice_id) AS notices_with_po,
  round(100.0 * count(DISTINCT pc.notice_id) / NULLIF(count(DISTINCT nc.notice_id),0), 2) AS conversion_pct
FROM notice_cat nc
LEFT JOIN po_cat pc
  ON pc.notice_id = nc.notice_id
 AND pc.category = nc.category
GROUP BY nc.category
HAVING count(DISTINCT nc.notice_id) >= 20
ORDER BY conversion_pct DESC, notices DESC;

-- [I7] Licitaciones con adjudicacion sin OC
SELECT
  n.notice_id,
  n.notice_title,
  n.notice_status_name,
  n.award_date,
  n.notice_awarded_line_count
FROM silver_notice n
LEFT JOIN silver_purchase_order p ON p.linked_notice_id = n.notice_id
LEFT JOIN silver_notice_purchase_order_link l ON l.notice_id = n.notice_id
WHERE (n.notice_awarded_line_count > 0 OR n.award_date IS NOT NULL)
  AND p.purchase_order_id IS NULL
  AND l.notice_purchase_order_link_id IS NULL
ORDER BY n.award_date DESC NULLS LAST;

-- [I8] OC sin licitacion enlazada
SELECT
  p.purchase_order_id,
  p.purchase_order_name,
  p.order_created_at,
  p.total_amount,
  p.purchase_order_status_name,
  p.supplier_key
FROM silver_purchase_order p
LEFT JOIN silver_notice n ON n.notice_id = p.linked_notice_id
WHERE p.linked_notice_id IS NULL
   OR n.notice_id IS NULL
ORDER BY p.order_created_at DESC NULLS LAST;

-- =====================================================================
-- J) TEXTO Y NLP READINESS
-- =====================================================================

-- [J1] Longitud promedio y null ratio por columna texto clave
WITH text_cols AS (
  SELECT 'silver_notice.notice_title' AS col, notice_title AS txt FROM silver_notice
  UNION ALL SELECT 'silver_notice.notice_description_raw', notice_description_raw FROM silver_notice
  UNION ALL SELECT 'silver_notice_line.line_name', line_name FROM silver_notice_line
  UNION ALL SELECT 'silver_notice_line.line_description_raw', line_description_raw FROM silver_notice_line
  UNION ALL SELECT 'silver_bid_submission.offer_name', offer_name FROM silver_bid_submission
  UNION ALL SELECT 'silver_purchase_order_line.buyer_item_spec_raw', buyer_item_spec_raw FROM silver_purchase_order_line
  UNION ALL SELECT 'silver_purchase_order_line.supplier_item_spec_raw', supplier_item_spec_raw FROM silver_purchase_order_line
)
SELECT
  col,
  count(*) AS rows_total,
  count(*) FILTER (WHERE txt IS NULL OR btrim(txt) = '') AS rows_null_or_empty,
  round(100.0 * count(*) FILTER (WHERE txt IS NULL OR btrim(txt) = '') / NULLIF(count(*),0), 2) AS null_pct,
  avg(length(txt)) FILTER (WHERE txt IS NOT NULL AND btrim(txt) <> '')::numeric(10,2) AS avg_len,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY length(txt)) FILTER (WHERE txt IS NOT NULL AND btrim(txt) <> '') AS p50_len
FROM text_cols
GROUP BY col
ORDER BY null_pct ASC, avg_len DESC;

-- [J2] Cantidad de textos unicos por columna
WITH text_cols AS (
  SELECT 'silver_notice.notice_title' AS col, notice_title AS txt FROM silver_notice
  UNION ALL SELECT 'silver_notice.notice_description_raw', notice_description_raw FROM silver_notice
  UNION ALL SELECT 'silver_notice_line.line_name', line_name FROM silver_notice_line
  UNION ALL SELECT 'silver_notice_line.line_description_raw', line_description_raw FROM silver_notice_line
  UNION ALL SELECT 'silver_purchase_order_line.buyer_item_spec_raw', buyer_item_spec_raw FROM silver_purchase_order_line
  UNION ALL SELECT 'silver_purchase_order_line.supplier_item_spec_raw', supplier_item_spec_raw FROM silver_purchase_order_line
)
SELECT
  col,
  count(*) FILTER (WHERE txt IS NOT NULL AND btrim(txt) <> '') AS non_null_rows,
  count(DISTINCT txt) FILTER (WHERE txt IS NOT NULL AND btrim(txt) <> '') AS unique_texts
FROM text_cols
GROUP BY col
ORDER BY unique_texts DESC;

-- [J3] Top tokens simples por columna (sin stopwords)
WITH src AS (
  SELECT 'notice_desc' AS source, notice_description_clean AS txt FROM silver_notice
  UNION ALL
  SELECT 'line_desc', line_description_clean FROM silver_notice_line
  UNION ALL
  SELECT 'buyer_spec', buyer_item_spec_clean FROM silver_purchase_order_line
  UNION ALL
  SELECT 'supplier_spec', supplier_item_spec_clean FROM silver_purchase_order_line
),
tokens AS (
  SELECT
    source,
    lower(token) AS token
  FROM src,
  LATERAL regexp_split_to_table(COALESCE(txt, ''), '[^a-zA-Z0-9]+') AS token
  WHERE token <> ''
    AND length(token) >= 3
)
SELECT source, token, count(*) AS freq
FROM tokens
GROUP BY source, token
ORDER BY source, freq DESC
LIMIT 200;

-- [J4] Top tokens por categoria (line_description_clean)
WITH base AS (
  SELECT
    COALESCE(category_level_3, category_level_2, category_level_1, 'SIN_CATEGORIA') AS category,
    line_description_clean
  FROM silver_notice_line
),
tokens AS (
  SELECT
    category,
    lower(token) AS token
  FROM base,
  LATERAL regexp_split_to_table(COALESCE(line_description_clean, ''), '[^a-zA-Z0-9]+') AS token
  WHERE token <> ''
    AND length(token) >= 3
)
SELECT category, token, count(*) AS freq
FROM tokens
GROUP BY category, token
ORDER BY category, freq DESC
LIMIT 300;

-- [J5] Top tokens por buyer (especificacion comprador)
WITH base AS (
  SELECT
    COALESCE(o.codigo_unidad_compra, 'SIN_BUYER') AS buyer_unit_code,
    i.especificacion_comprador AS txt
  FROM normalized_ordenes_compra o
  JOIN normalized_ordenes_compra_items i ON i.codigo_oc = o.codigo_oc
),
tokens AS (
  SELECT
    buyer_unit_code,
    lower(token) AS token
  FROM base,
  LATERAL regexp_split_to_table(COALESCE(txt, ''), '[^a-zA-Z0-9]+') AS token
  WHERE token <> ''
    AND length(token) >= 3
)
SELECT buyer_unit_code, token, count(*) AS freq
FROM tokens
GROUP BY buyer_unit_code, token
HAVING count(*) >= 5
ORDER BY freq DESC
LIMIT 300;

-- [J6] Overlap lexico notice vs OC (linked_notice_id)
WITH pair_text AS (
  SELECT
    p.purchase_order_id,
    p.linked_notice_id AS notice_id,
    string_to_array(regexp_replace(COALESCE(n.notice_description_clean, ''), '\\s+', ' ', 'g'), ' ') AS notice_tokens,
    string_to_array(regexp_replace(COALESCE(string_agg(pol.buyer_item_spec_clean, ' '), ''), '\\s+', ' ', 'g'), ' ') AS po_tokens
  FROM silver_purchase_order p
  JOIN silver_notice n ON n.notice_id = p.linked_notice_id
  LEFT JOIN silver_purchase_order_line pol ON pol.purchase_order_id = p.purchase_order_id
  WHERE p.linked_notice_id IS NOT NULL
  GROUP BY p.purchase_order_id, p.linked_notice_id, n.notice_description_clean
),
sets AS (
  SELECT
    purchase_order_id,
    notice_id,
    ARRAY(
      SELECT DISTINCT t FROM unnest(notice_tokens) AS t
      WHERE t <> '' AND length(t) >= 3
    ) AS nset,
    ARRAY(
      SELECT DISTINCT t FROM unnest(po_tokens) AS t
      WHERE t <> '' AND length(t) >= 3
    ) AS pset
  FROM pair_text
)
SELECT
  purchase_order_id,
  notice_id,
  cardinality(nset) AS notice_vocab,
  cardinality(pset) AS po_vocab,
  cardinality(ARRAY(SELECT unnest(nset) INTERSECT SELECT unnest(pset))) AS overlap_terms
FROM sets
ORDER BY overlap_terms DESC, notice_vocab DESC
LIMIT 200;

-- [J7] Densidad semantica simple por columna (tokens_unicos / tokens_totales)
WITH text_cols AS (
  SELECT 'notice_description_clean' AS col, notice_description_clean AS txt FROM silver_notice
  UNION ALL SELECT 'line_description_clean', line_description_clean FROM silver_notice_line
  UNION ALL SELECT 'buyer_item_spec_clean', buyer_item_spec_clean FROM silver_purchase_order_line
  UNION ALL SELECT 'supplier_item_spec_clean', supplier_item_spec_clean FROM silver_purchase_order_line
),
tokens AS (
  SELECT
    col,
    lower(token) AS token
  FROM text_cols,
  LATERAL regexp_split_to_table(COALESCE(txt, ''), '[^a-zA-Z0-9]+') AS token
  WHERE token <> ''
    AND length(token) >= 3
)
SELECT
  col,
  count(*) AS token_total,
  count(DISTINCT token) AS token_unique,
  round(count(DISTINCT token)::numeric / NULLIF(count(*),0), 4) AS semantic_density_ratio
FROM tokens
GROUP BY col
ORDER BY semantic_density_ratio DESC;

-- [J8] NLP readiness score por columna
WITH prof AS (
  SELECT
    col,
    avg_len,
    null_pct,
    unique_texts,
    non_null_rows,
    CASE WHEN non_null_rows > 0 THEN unique_texts::numeric / non_null_rows ELSE 0 END AS uniqueness_ratio
  FROM (
    WITH text_cols AS (
      SELECT 'silver_notice.notice_description_raw' AS col, notice_description_raw AS txt FROM silver_notice
      UNION ALL SELECT 'silver_notice_line.line_description_raw', line_description_raw FROM silver_notice_line
      UNION ALL SELECT 'silver_purchase_order_line.buyer_item_spec_raw', buyer_item_spec_raw FROM silver_purchase_order_line
      UNION ALL SELECT 'silver_purchase_order_line.supplier_item_spec_raw', supplier_item_spec_raw FROM silver_purchase_order_line
    )
    SELECT
      col,
      avg(length(txt)) FILTER (WHERE txt IS NOT NULL AND btrim(txt) <> '')::numeric(10,2) AS avg_len,
      round(100.0 * count(*) FILTER (WHERE txt IS NULL OR btrim(txt) = '') / NULLIF(count(*),0), 2) AS null_pct,
      count(DISTINCT txt) FILTER (WHERE txt IS NOT NULL AND btrim(txt) <> '') AS unique_texts,
      count(*) FILTER (WHERE txt IS NOT NULL AND btrim(txt) <> '') AS non_null_rows
    FROM text_cols
    GROUP BY col
  ) x
)
SELECT
  col,
  avg_len,
  null_pct,
  unique_texts,
  round(uniqueness_ratio, 4) AS uniqueness_ratio,
  round(
    greatest(0, 100 - null_pct)
    + least(avg_len, 200) * 0.2
    + least(uniqueness_ratio * 100, 100) * 0.4,
    2
  ) AS nlp_readiness_score
FROM prof
ORDER BY nlp_readiness_score DESC;

-- =====================================================================
-- K) CALIDAD DE DATOS Y JOINS
-- =====================================================================

-- [K1] Null ratio columnas llave clave
SELECT * FROM (
  SELECT 'silver_notice.notice_id' AS key_col, round(100.0 * avg((notice_id IS NULL)::int), 2) AS null_pct FROM silver_notice
  UNION ALL SELECT 'silver_notice_line.notice_id', round(100.0 * avg((notice_id IS NULL)::int), 2) FROM silver_notice_line
  UNION ALL SELECT 'silver_bid_submission.notice_id', round(100.0 * avg((notice_id IS NULL)::int), 2) FROM silver_bid_submission
  UNION ALL SELECT 'silver_purchase_order.purchase_order_id', round(100.0 * avg((purchase_order_id IS NULL)::int), 2) FROM silver_purchase_order
  UNION ALL SELECT 'silver_purchase_order.linked_notice_id', round(100.0 * avg((linked_notice_id IS NULL)::int), 2) FROM silver_purchase_order
  UNION ALL SELECT 'normalized_ordenes_compra.codigo_licitacion', round(100.0 * avg((codigo_licitacion IS NULL)::int), 2) FROM normalized_ordenes_compra
  UNION ALL SELECT 'normalized_ordenes_compra.buyer_key', round(100.0 * avg((buyer_key IS NULL)::int), 2) FROM normalized_ordenes_compra
  UNION ALL SELECT 'normalized_ordenes_compra.supplier_key', round(100.0 * avg((supplier_key IS NULL)::int), 2) FROM normalized_ordenes_compra
) t
ORDER BY null_pct DESC;

-- [K2] Duplicados por llave de negocio
SELECT 'silver_notice_line (notice_id,item_code)' AS entity, count(*) AS duplicate_groups
FROM (
  SELECT notice_id, item_code
  FROM silver_notice_line
  GROUP BY 1,2
  HAVING count(*) > 1
) d
UNION ALL
SELECT 'silver_purchase_order_line (purchase_order_id,line_item_id)', count(*)
FROM (
  SELECT purchase_order_id, line_item_id
  FROM silver_purchase_order_line
  GROUP BY 1,2
  HAVING count(*) > 1
) d
UNION ALL
SELECT 'normalized_licitacion_items (codigo_externo,codigo_item)', count(*)
FROM (
  SELECT codigo_externo, codigo_item
  FROM normalized_licitacion_items
  GROUP BY 1,2
  HAVING count(*) > 1
) d;

-- [K3] Filas huerfanas en joins importantes
SELECT 'bid_without_notice' AS issue, count(*) AS rows
FROM silver_bid_submission b
LEFT JOIN silver_notice n ON n.notice_id = b.notice_id
WHERE n.notice_id IS NULL
UNION ALL
SELECT 'award_without_notice', count(*)
FROM silver_award_outcome a
LEFT JOIN silver_notice n ON n.notice_id = a.notice_id
WHERE n.notice_id IS NULL
UNION ALL
SELECT 'po_line_without_po', count(*)
FROM silver_purchase_order_line l
LEFT JOIN silver_purchase_order p ON p.purchase_order_id = l.purchase_order_id
WHERE p.purchase_order_id IS NULL
UNION ALL
SELECT 'normalized_oc_item_without_oc', count(*)
FROM normalized_ordenes_compra_items i
LEFT JOIN normalized_ordenes_compra o ON o.codigo_oc = i.codigo_oc
WHERE o.codigo_oc IS NULL;

-- [K4] Buyers sin notices u OCs
SELECT
  b.buyer_key,
  count(DISTINCT l.codigo_externo) AS notices,
  count(DISTINCT o.codigo_oc) AS po
FROM normalized_buyers b
LEFT JOIN normalized_licitaciones l ON l.codigo_unidad = b.codigo_unidad_compra
LEFT JOIN normalized_ordenes_compra o ON o.buyer_key = b.buyer_key
GROUP BY b.buyer_key
HAVING count(DISTINCT l.codigo_externo) = 0 OR count(DISTINCT o.codigo_oc) = 0
ORDER BY po, notices;

-- [K5] Suppliers sin ofertas u OCs
SELECT
  s.supplier_key,
  count(DISTINCT f.oferta_key_sha256) AS offers,
  count(DISTINCT o.codigo_oc) AS po
FROM normalized_suppliers s
LEFT JOIN normalized_ofertas f ON f.supplier_key = s.supplier_key
LEFT JOIN normalized_ordenes_compra o ON o.supplier_key = s.supplier_key
GROUP BY s.supplier_key
HAVING count(DISTINCT f.oferta_key_sha256) = 0 OR count(DISTINCT o.codigo_oc) = 0
ORDER BY po, offers;

-- [K6] Licitaciones sin lineas + lineas sin categoria
SELECT 'notice_without_lines' AS issue, count(*) AS rows
FROM normalized_licitaciones l
LEFT JOIN normalized_licitacion_items i ON i.codigo_externo = l.codigo_externo
WHERE i.id IS NULL
UNION ALL
SELECT 'notice_line_without_category', count(*)
FROM silver_notice_line
WHERE category_level_1 IS NULL AND category_level_2 IS NULL AND category_level_3 IS NULL;

-- [K7] OC sin supplier o sin buyer
SELECT 'normalized_oc_without_supplier_key' AS issue, count(*) AS rows
FROM normalized_ordenes_compra
WHERE supplier_key IS NULL
UNION ALL
SELECT 'normalized_oc_without_buyer_key', count(*)
FROM normalized_ordenes_compra
WHERE buyer_key IS NULL
UNION ALL
SELECT 'silver_po_without_supplier_key', count(*)
FROM silver_purchase_order
WHERE supplier_key IS NULL;

-- [K8] Valores monetarios negativos o sospechosos
SELECT 'silver_purchase_order.total_amount_negative' AS issue, count(*) AS rows
FROM silver_purchase_order
WHERE total_amount < 0
UNION ALL
SELECT 'silver_purchase_order_line.line_net_total_negative', count(*)
FROM silver_purchase_order_line
WHERE line_net_total < 0
UNION ALL
SELECT 'normalized_ordenes_compra.monto_total_oc_negative', count(*)
FROM normalized_ordenes_compra
WHERE monto_total_oc < 0
UNION ALL
SELECT 'normalized_ordenes_compra_items.total_linea_neto_negative', count(*)
FROM normalized_ordenes_compra_items
WHERE total_linea_neto < 0;

-- [K9] Fechas inconsistentes
SELECT 'notice_publication_after_close' AS issue, count(*) AS rows
FROM silver_notice
WHERE publication_date IS NOT NULL AND close_date IS NOT NULL AND publication_date > close_date
UNION ALL
SELECT 'notice_close_after_award', count(*)
FROM silver_notice
WHERE close_date IS NOT NULL AND award_date IS NOT NULL AND close_date > award_date
UNION ALL
SELECT 'po_accept_before_create', count(*)
FROM silver_purchase_order
WHERE order_created_at IS NOT NULL AND order_accepted_at IS NOT NULL AND order_accepted_at < order_created_at
UNION ALL
SELECT 'po_cancel_before_create', count(*)
FROM silver_purchase_order
WHERE order_created_at IS NOT NULL AND order_cancelled_at IS NOT NULL AND order_cancelled_at < order_created_at;

-- [K10] Alta fragmentacion de nombres proveedor
WITH norm AS (
  SELECT
    codigo_proveedor,
    regexp_replace(lower(trim(coalesce(nombre_proveedor, ''))), '\\s+', ' ', 'g') AS supplier_name_norm
  FROM normalized_ordenes_compra
  WHERE codigo_proveedor IS NOT NULL
)
SELECT
  codigo_proveedor,
  count(DISTINCT supplier_name_norm) AS distinct_name_variants,
  array_agg(DISTINCT supplier_name_norm ORDER BY supplier_name_norm) AS sample_names
FROM norm
GROUP BY codigo_proveedor
HAVING count(DISTINCT supplier_name_norm) >= 3
ORDER BY distinct_name_variants DESC, codigo_proveedor
LIMIT 200;

